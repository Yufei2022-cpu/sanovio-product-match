"""
Candidate generation: reduces N×M hospital-supplier product pairs
to N×K plausible candidates using category filtering + text similarity.

Strategy:
1. Hard filter: only compare products in the same product_category.
2. Identifier match: GTIN/EAN/PZN overlap → immediate high-priority candidate.
3. Text similarity: Jaccard token overlap on normalized product names.
4. Attribute similarity: bonus score for matching size/dimensions.
5. Return top-K candidates per hospital article, ranked by combined score.

Design decision: For the sample size (~10 hospital articles, ~30 supplier products),
in-memory scoring is efficient. No vector database or embedding model needed.
"""

from sqlalchemy.orm import Session
from backend.app.models import HospitalArticle, SupplierProduct
from backend.app.ingestion.normalizer import tokenize, normalize_text
from dataclasses import dataclass


@dataclass
class CandidateMatch:
    """A potential supplier product match for a hospital article."""
    supplier_product_id: int
    score: float
    rank: int
    match_reasons: list[str]


def generate_candidates(
    hospital_article: HospitalArticle,
    supplier_products: list[SupplierProduct],
    top_k: int = 5,
) -> list[CandidateMatch]:
    """
    Generate ranked candidate supplier products for a hospital article.

    Returns up to top_k candidates sorted by descending score.
    Products with no category overlap receive a score of 0 and are excluded.
    """
    scored_candidates = []

    for sp in supplier_products:
        score, reasons = _score_candidate(hospital_article, sp)
        if score > 0:
            scored_candidates.append((sp.id, score, reasons))

    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[1], reverse=True)

    # Take top-K
    results = []
    for rank, (sp_id, score, reasons) in enumerate(scored_candidates[:top_k], 1):
        results.append(CandidateMatch(
            supplier_product_id=sp_id,
            score=round(score, 3),
            rank=rank,
            match_reasons=reasons,
        ))

    return results


def _score_candidate(
    hospital: HospitalArticle,
    supplier: SupplierProduct,
) -> tuple[float, list[str]]:
    """
    Score a supplier product as a candidate for a hospital article.
    Returns (score, list_of_reasons).
    Score 0.0 means not a candidate at all.
    """
    score = 0.0
    reasons = []

    # --- 1. Category filter (hard gate) ---
    if hospital.product_category and supplier.product_category:
        if hospital.product_category != supplier.product_category:
            return 0.0, []
        score += 0.3
        reasons.append(f"Same category: {hospital.product_category}")
    elif hospital.product_category or supplier.product_category:
        # One has a category, the other doesn't — weak signal
        return 0.0, []
    # Neither has a category — fall through to text matching

    # --- 2. Identifier matching ---
    if hospital.gtin and supplier.gtin and hospital.gtin == supplier.gtin:
        score += 0.5
        reasons.append("GTIN match")
    if hospital.ean and supplier.ean and hospital.ean == supplier.ean:
        score += 0.5
        reasons.append("EAN match")
    if hospital.article_number and supplier.pzn and hospital.article_number == supplier.pzn:
        score += 0.3
        reasons.append("Article number matches PZN")

    # --- 3. Text similarity (Jaccard on normalized tokens) ---
    h_tokens = tokenize(hospital.raw_name)
    s_tokens = tokenize(supplier.raw_name)

    if h_tokens and s_tokens:
        intersection = h_tokens & s_tokens
        union = h_tokens | s_tokens
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0.1:
            score += jaccard * 0.3
            reasons.append(f"Name similarity: {jaccard:.2f}")

    # --- 4. Size / dimension match ---
    if hospital.size_label and supplier.size_label:
        h_size = normalize_text(hospital.size_label)
        s_size = normalize_text(supplier.size_label)
        if h_size == s_size:
            score += 0.25
            reasons.append(f"Size match: {hospital.size_label}")
        elif _dimensions_compatible(hospital, supplier):
            score += 0.15
            reasons.append("Dimensions partially match")

    # --- 5. Connector type match (for syringes/needles) ---
    if hospital.connector_type and supplier.connector_type:
        if hospital.connector_type == supplier.connector_type:
            score += 0.1
            reasons.append(f"Connector match: {hospital.connector_type}")

    # --- 6. Sterility alignment ---
    if hospital.sterility and supplier.sterility:
        if hospital.sterility == supplier.sterility:
            score += 0.05
            reasons.append("Sterility match")

    return score, reasons


def _dimensions_compatible(
    hospital: HospitalArticle,
    supplier: SupplierProduct,
) -> bool:
    """Check if numeric dimensions are close enough to be plausible candidates."""
    h_dims = hospital.dimensions
    s_dims = supplier.dimensions

    if not h_dims or not s_dims:
        return False

    # Syringe volume comparison
    h_vol = h_dims.get("volume_ml")
    s_vol = s_dims.get("volume_ml")
    if h_vol is not None and s_vol is not None:
        return abs(h_vol - s_vol) / max(h_vol, s_vol) < 0.01  # Must be same volume

    # Needle dimension comparison
    h_od = h_dims.get("od_mm")
    s_od = s_dims.get("od_mm")
    h_len = h_dims.get("length_mm")
    s_len = s_dims.get("length_mm")

    if h_od is not None and s_od is not None:
        if abs(h_od - s_od) > 0.01:  # OD must match exactly
            return False
        if h_len is not None and s_len is not None:
            return abs(h_len - s_len) < 0.1
        return True  # OD matches, length unknown

    return False
