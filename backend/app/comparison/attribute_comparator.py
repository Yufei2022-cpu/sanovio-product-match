"""
Attribute comparator: performs per-attribute comparison between a hospital
article and a supplier product. Returns structured evidence for each attribute.

Design principles:
- Hard constraints (category, sterility) can produce immediate INCOMPATIBLE.
- Missing critical attributes produce UNCERTAIN, not a guess.
- Brand/manufacturer differences are INFORMATIONAL, never blockers.
- Numeric dimensions use tolerance-aware comparison.
"""

from dataclasses import dataclass, field
from typing import Optional
from backend.app.models import HospitalArticle, SupplierProduct
from backend.app.ingestion.normalizer import normalize_text


@dataclass
class AttributeComparison:
    """Result of comparing a single attribute between hospital and supplier."""
    attribute_name: str
    hospital_value: Optional[str]
    supplier_value: Optional[str]
    status: str  # "match" | "conflict" | "missing" | "not_applicable"
    criticality: str  # "hard_blocker" | "critical" | "important" | "informational"
    note: Optional[str] = None


@dataclass
class ComparisonEvidence:
    """Full comparison evidence across all attributes."""
    comparisons: list[AttributeComparison] = field(default_factory=list)
    matching: list[AttributeComparison] = field(default_factory=list)
    conflicting: list[AttributeComparison] = field(default_factory=list)
    missing_critical: list[AttributeComparison] = field(default_factory=list)

    @property
    def has_hard_conflicts(self) -> bool:
        return any(
            c.status == "conflict" and c.criticality == "hard_blocker"
            for c in self.comparisons
        )

    @property
    def has_critical_missing(self) -> bool:
        return any(
            c.status == "missing" and c.criticality in ("hard_blocker", "critical")
            for c in self.comparisons
        )

    @property
    def has_any_conflicts(self) -> bool:
        return any(c.status == "conflict" for c in self.comparisons)


def compare_attributes(
    hospital: HospitalArticle,
    supplier: SupplierProduct,
) -> ComparisonEvidence:
    """
    Compare all relevant attributes between a hospital article and supplier product.
    Returns structured evidence for decision making.
    """
    evidence = ComparisonEvidence()

    # --- Product Category (HARD BLOCKER) ---
    evidence.comparisons.append(_compare_category(hospital, supplier))

    # --- Sterility (HARD BLOCKER) ---
    evidence.comparisons.append(_compare_sterility(hospital, supplier))

    # --- Material (CRITICAL for gloves, IMPORTANT for others) ---
    evidence.comparisons.append(_compare_material(hospital, supplier))

    # --- Size / Dimensions (CRITICAL) ---
    evidence.comparisons.append(_compare_size(hospital, supplier))

    # --- Connector Type (CRITICAL for syringes) ---
    evidence.comparisons.append(_compare_connector(hospital, supplier))

    # --- MDR Class (CRITICAL) ---
    evidence.comparisons.append(_compare_mdr_class(hospital, supplier))

    # --- Packaging (IMPORTANT) ---
    evidence.comparisons.append(_compare_packaging(hospital, supplier))

    # --- Brand / Manufacturer (INFORMATIONAL — never a blocker) ---
    evidence.comparisons.append(_compare_brand(hospital, supplier))

    # Categorize
    for comp in evidence.comparisons:
        if comp.status == "match":
            evidence.matching.append(comp)
        elif comp.status == "conflict":
            evidence.conflicting.append(comp)
        elif comp.status == "missing" and comp.criticality in ("hard_blocker", "critical"):
            evidence.missing_critical.append(comp)

    return evidence


# ---------------------------------------------------------------------------
# Individual attribute comparators
# ---------------------------------------------------------------------------

def _compare_category(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """Product category — HARD BLOCKER if different."""
    h_val = h.product_category
    s_val = s.product_category

    if not h_val or not s_val:
        return AttributeComparison(
            "product_category", h_val, s_val, "missing", "hard_blocker",
            "Product category unknown for one or both products"
        )

    if h_val == s_val:
        return AttributeComparison(
            "product_category", h_val, s_val, "match", "hard_blocker",
            f"Both are: {h_val}"
        )

    return AttributeComparison(
        "product_category", h_val, s_val, "conflict", "hard_blocker",
        f"Category mismatch: {h_val} vs {s_val}"
    )


def _compare_sterility(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """Sterility — HARD BLOCKER. Missing = UNCERTAIN, never guess."""
    h_val = h.sterility
    s_val = s.sterility

    if not h_val and not s_val:
        return AttributeComparison(
            "sterility", h_val, s_val, "missing", "hard_blocker",
            "Sterility information unknown for both products"
        )

    if not s_val:
        return AttributeComparison(
            "sterility", h_val, s_val, "missing", "hard_blocker",
            "Supplier product sterility not specified — cannot verify safety"
        )

    if not h_val:
        return AttributeComparison(
            "sterility", h_val, s_val, "missing", "hard_blocker",
            "Hospital article sterility not specified"
        )

    h_norm = normalize_text(h_val)
    s_norm = normalize_text(s_val)

    if h_norm == s_norm:
        return AttributeComparison(
            "sterility", h_val, s_val, "match", "hard_blocker",
            f"Both: {h_val}"
        )

    # sterile vs non-sterile is a hard conflict
    return AttributeComparison(
        "sterility", h_val, s_val, "conflict", "hard_blocker",
        f"Sterility conflict: hospital requires '{h_val}', supplier provides '{s_val}'"
    )


def _compare_material(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """
    Material — CRITICAL for gloves (latex allergy risk), IMPORTANT for others.
    """
    h_val = h.material
    s_val = s.material

    # Determine criticality based on category
    is_glove = h.product_category == "glove"
    criticality = "critical" if is_glove else "important"

    if not h_val and not s_val:
        return AttributeComparison(
            "material", h_val, s_val, "not_applicable", criticality,
            "Material not specified for either product"
        )

    if not h_val or not s_val:
        missing_side = "supplier" if not s_val else "hospital"
        return AttributeComparison(
            "material", h_val, s_val, "missing", criticality,
            f"Material not specified for {missing_side} product"
        )

    h_norm = normalize_text(h_val)
    s_norm = normalize_text(s_val)

    if h_norm == s_norm:
        return AttributeComparison(
            "material", h_val, s_val, "match", criticality,
            f"Both: {h_val}"
        )

    # Different materials — conflict severity depends on context
    return AttributeComparison(
        "material", h_val, s_val, "conflict", criticality,
        f"Material difference: {h_val} vs {s_val}"
    )


def _compare_size(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """Size / dimensions — CRITICAL."""
    h_val = h.size_label
    s_val = s.size_label

    if not h_val and not s_val:
        return AttributeComparison(
            "size", h_val, s_val, "not_applicable", "critical",
            "No size information available"
        )

    if not h_val or not s_val:
        missing_side = "supplier" if not s_val else "hospital"
        return AttributeComparison(
            "size", h_val, s_val, "missing", "critical",
            f"Size not specified for {missing_side} product"
        )

    # Try exact match first
    if normalize_text(h_val) == normalize_text(s_val):
        return AttributeComparison(
            "size", h_val, s_val, "match", "critical",
            f"Exact size match: {h_val}"
        )

    # Try numeric dimension comparison
    h_dims = h.dimensions
    s_dims = s.dimensions

    if h_dims and s_dims:
        # Volume comparison
        h_vol = h_dims.get("volume_ml")
        s_vol = s_dims.get("volume_ml")
        if h_vol is not None and s_vol is not None:
            if abs(h_vol - s_vol) < 0.01:
                return AttributeComparison(
                    "size", h_val, s_val, "match", "critical",
                    f"Volume match: {h_vol} ml"
                )
            return AttributeComparison(
                "size", h_val, s_val, "conflict", "critical",
                f"Volume mismatch: {h_vol} ml vs {s_vol} ml"
            )

        # Needle dimension comparison
        h_od = h_dims.get("od_mm")
        s_od = s_dims.get("od_mm")
        h_len = h_dims.get("length_mm")
        s_len = s_dims.get("length_mm")

        if h_od is not None and s_od is not None:
            od_match = abs(h_od - s_od) < 0.01
            len_match = (h_len is None or s_len is None or abs(h_len - s_len) < 0.1)

            if od_match and len_match:
                return AttributeComparison(
                    "size", h_val, s_val, "match", "critical",
                    f"Dimensions match: {h_val}"
                )
            if not od_match:
                return AttributeComparison(
                    "size", h_val, s_val, "conflict", "critical",
                    f"Diameter mismatch: {h_od}mm vs {s_od}mm"
                )
            return AttributeComparison(
                "size", h_val, s_val, "conflict", "critical",
                f"Length mismatch: {h_len}mm vs {s_len}mm"
            )

    return AttributeComparison(
        "size", h_val, s_val, "conflict", "critical",
        f"Size mismatch: {h_val} vs {s_val}"
    )


def _compare_connector(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """Connector type — CRITICAL for syringes/needles."""
    h_val = h.connector_type
    s_val = s.connector_type

    # Only relevant for syringes and needles
    relevant_categories = {"syringe", "needle", "pen_needle", "filter_needle"}
    is_relevant = (
        (h.product_category in relevant_categories) or
        (s.product_category in relevant_categories)
    )

    if not is_relevant:
        return AttributeComparison(
            "connector_type", h_val, s_val, "not_applicable", "critical",
            "Connector type not relevant for this product category"
        )

    if not h_val and not s_val:
        return AttributeComparison(
            "connector_type", h_val, s_val, "missing", "critical",
            "Connector type unknown for both products"
        )

    if not h_val or not s_val:
        return AttributeComparison(
            "connector_type", h_val, s_val, "missing", "critical",
            f"Connector type not specified for {'supplier' if not s_val else 'hospital'} product"
        )

    if h_val == s_val:
        return AttributeComparison(
            "connector_type", h_val, s_val, "match", "critical",
            f"Connector match: {h_val}"
        )

    # Conditional compatibility: Luer fits into Luer-Lock (but not vice versa)
    if h_val == "luer-lock" and s_val == "luer":
        return AttributeComparison(
            "connector_type", h_val, s_val, "conflict", "critical",
            "Hospital requires Luer-Lock, supplier provides Luer (Steck) — "
            "Luer does not lock into Luer-Lock receptacles securely"
        )

    if h_val == "luer" and s_val == "luer-lock":
        return AttributeComparison(
            "connector_type", h_val, s_val, "match", "critical",
            "Hospital uses Luer, supplier provides Luer-Lock — compatible "
            "(Luer-Lock accepts Luer connections)"
        )

    return AttributeComparison(
        "connector_type", h_val, s_val, "conflict", "critical",
        f"Connector mismatch: {h_val} vs {s_val}"
    )


def _compare_mdr_class(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """MDR classification — CRITICAL."""
    h_val = h.mdr_class
    s_val = s.mdr_class

    if not h_val and not s_val:
        return AttributeComparison(
            "mdr_class", h_val, s_val, "missing", "critical",
            "MDR classification unknown for both products"
        )

    if not s_val:
        return AttributeComparison(
            "mdr_class", h_val, s_val, "missing", "critical",
            "Supplier product MDR classification not specified"
        )

    if not h_val:
        return AttributeComparison(
            "mdr_class", h_val, s_val, "missing", "critical",
            "Hospital article MDR classification not specified"
        )

    if h_val == s_val:
        return AttributeComparison(
            "mdr_class", h_val, s_val, "match", "critical",
            f"MDR class match: {h_val}"
        )

    # Risk class ordering: I < IIa < IIb < III
    risk_order = {"I": 1, "IIa": 2, "IIb": 3, "III": 4}
    h_risk = risk_order.get(h_val, 0)
    s_risk = risk_order.get(s_val, 0)

    if s_risk < h_risk:
        return AttributeComparison(
            "mdr_class", h_val, s_val, "match", "critical",
            f"Supplier has lower risk class ({s_val} < {h_val}) — acceptable"
        )

    return AttributeComparison(
        "mdr_class", h_val, s_val, "conflict", "critical",
        f"Supplier has higher risk class ({s_val} > {h_val}) — may require review"
    )


def _compare_packaging(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """Packaging quantity — IMPORTANT but not a blocker."""
    h_val = str(h.base_units_per_order_unit) if h.base_units_per_order_unit else None
    s_val = str(s.units_per_package) if s.units_per_package else None

    if not h_val or not s_val:
        return AttributeComparison(
            "packaging", h_val, s_val, "not_applicable", "important",
            "Packaging information not fully available"
        )

    if h_val == s_val:
        return AttributeComparison(
            "packaging", f"{h_val} per {h.order_unit}", f"{s_val} per pkg",
            "match", "important",
            f"Same packaging quantity: {h_val}"
        )

    return AttributeComparison(
        "packaging",
        f"{h_val} per {h.order_unit or 'unit'}",
        f"{s_val} per pkg",
        "conflict", "important",
        f"Different packaging: {h_val} vs {s_val} per unit"
    )


def _compare_brand(h: HospitalArticle, s: SupplierProduct) -> AttributeComparison:
    """Brand / manufacturer — INFORMATIONAL only, never a blocker."""
    h_val = h.brand or h.manufacturer
    s_val = s.brand or s.manufacturer

    if not h_val or not s_val:
        return AttributeComparison(
            "brand", h_val, s_val, "not_applicable", "informational",
            "Brand information not fully available"
        )

    if normalize_text(h_val) == normalize_text(s_val):
        return AttributeComparison(
            "brand", h_val, s_val, "match", "informational",
            f"Same brand: {h_val}"
        )

    return AttributeComparison(
        "brand", h_val, s_val, "match", "informational",
        f"Different brand ({h_val} vs {s_val}) — not a compatibility factor"
    )
