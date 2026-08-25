"""
Decision engine: aggregates per-attribute evidence into a final
COMPATIBLE / INCOMPATIBLE / UNCERTAIN decision with confidence score,
explanation, and supplier questions for missing information.

Design principles:
- Hard conflicts → INCOMPATIBLE (no override)
- Missing critical attributes → UNCERTAIN (favor abstention)
- All critical attributes present and matching → COMPATIBLE
- Confidence reflects the completeness and clarity of evidence
"""

from backend.app.models import (
    HospitalArticle, SupplierProduct, Comparison, ComparisonEvidence as EvidenceModel,
    InformationRequest,
)
from backend.app.comparison.attribute_comparator import (
    compare_attributes, ComparisonEvidence, AttributeComparison,
)
from sqlalchemy.orm import Session


def run_comparison(
    hospital: HospitalArticle,
    supplier: SupplierProduct,
    candidate_rank: int = 0,
    candidate_score: float = 0.0,
    db: Session = None,
) -> dict:
    """
    Run full comparison between a hospital article and supplier product.

    Returns a dict with decision, confidence, evidence, and questions.
    If db is provided, persists the comparison and related records.
    """
    # 1. Compare all attributes
    evidence = compare_attributes(hospital, supplier)

    # 2. Make decision
    decision, confidence = _make_decision(evidence)

    # 3. Generate explanation
    summary = _generate_summary(hospital, supplier, evidence, decision)
    reasoning = _generate_reasoning(evidence, decision)

    # 4. Generate supplier questions for missing critical attributes
    questions = _generate_questions(hospital, supplier, evidence)

    result = {
        "decision": decision,
        "confidence": confidence,
        "summary": summary,
        "reasoning_summary": reasoning,
        "matching_attributes": [_attr_to_dict(a) for a in evidence.matching],
        "conflicting_attributes": [_attr_to_dict(a) for a in evidence.conflicting],
        "missing_critical_attributes": [_attr_to_dict(a) for a in evidence.missing_critical],
        "all_evidence": [_attr_to_dict(a) for a in evidence.comparisons],
        "supplier_questions": questions,
        "candidate_rank": candidate_rank,
        "candidate_score": candidate_score,
    }

    # 5. Persist if db provided
    if db:
        _persist_comparison(
            db, hospital, supplier, result, evidence, candidate_rank, candidate_score
        )

    return result


def _make_decision(evidence: ComparisonEvidence) -> tuple[str, float]:
    """
    Determine decision and confidence from evidence.

    Rules:
    1. Any hard-blocker conflict → INCOMPATIBLE
    2. Any critical/hard-blocker missing → UNCERTAIN
    3. Any critical conflict → INCOMPATIBLE
    4. Otherwise → COMPATIBLE
    """
    if evidence.has_hard_conflicts:
        # Count severity
        hard_conflicts = [c for c in evidence.comparisons
                          if c.status == "conflict" and c.criticality == "hard_blocker"]
        confidence = min(0.95, 0.7 + 0.1 * len(hard_conflicts))
        return "incompatible", confidence

    if evidence.has_critical_missing:
        # More missing = lower confidence
        n_missing = len(evidence.missing_critical)
        confidence = max(0.3, 0.6 - 0.1 * n_missing)
        return "uncertain", confidence

    # Check for non-hard-blocker conflicts
    critical_conflicts = [c for c in evidence.comparisons
                          if c.status == "conflict" and c.criticality == "critical"]
    if critical_conflicts:
        confidence = min(0.85, 0.6 + 0.1 * len(critical_conflicts))
        return "incompatible", confidence

    important_conflicts = [c for c in evidence.comparisons
                           if c.status == "conflict" and c.criticality == "important"]
    if important_conflicts:
        # Important conflicts don't block but reduce confidence
        n_matches = len(evidence.matching)
        confidence = max(0.5, 0.8 - 0.05 * len(important_conflicts))
        return "compatible", confidence

    # All good — compatible
    n_matches = len(evidence.matching)
    n_total = len([c for c in evidence.comparisons
                   if c.status != "not_applicable"])
    if n_total > 0:
        confidence = min(0.95, 0.7 + 0.05 * n_matches)
    else:
        confidence = 0.5

    return "compatible", confidence


def _generate_summary(
    hospital: HospitalArticle,
    supplier: SupplierProduct,
    evidence: ComparisonEvidence,
    decision: str,
) -> str:
    """Generate a concise business-facing summary."""
    h_name = hospital.raw_name
    s_name = supplier.raw_name

    if decision == "incompatible":
        conflicts = [c for c in evidence.conflicting]
        conflict_attrs = ", ".join(c.attribute_name for c in conflicts[:3])
        return (
            f'"{s_name}" cannot replace "{h_name}". '
            f"Key conflicts: {conflict_attrs}."
        )

    if decision == "uncertain":
        missing = [c for c in evidence.missing_critical]
        missing_attrs = ", ".join(c.attribute_name for c in missing[:3])
        return (
            f'"{s_name}" may be able to replace "{h_name}", '
            f"but critical information is missing: {missing_attrs}. "
            f"A definitive assessment requires additional supplier information."
        )

    # Compatible
    matches = [c for c in evidence.matching]
    match_attrs = ", ".join(c.attribute_name for c in matches[:4])
    return (
        f'"{s_name}" appears suitable to replace "{h_name}". '
        f"Matching attributes: {match_attrs}."
    )


def _generate_reasoning(evidence: ComparisonEvidence, decision: str) -> str:
    """Generate structured reasoning from observable attributes."""
    parts = []

    matches = evidence.matching
    if matches:
        parts.append(f"Matching attributes ({len(matches)}): " +
                      ", ".join(f"{c.attribute_name} ({c.note})" for c in matches))

    conflicts = evidence.conflicting
    if conflicts:
        parts.append(f"Conflicting attributes ({len(conflicts)}): " +
                      ", ".join(f"{c.attribute_name} ({c.note})" for c in conflicts))

    missing = evidence.missing_critical
    if missing:
        parts.append(f"Missing critical information ({len(missing)}): " +
                      ", ".join(f"{c.attribute_name} ({c.note})" for c in missing))

    return " | ".join(parts)


def _generate_questions(
    hospital: HospitalArticle,
    supplier: SupplierProduct,
    evidence: ComparisonEvidence,
) -> list[dict]:
    """Generate targeted supplier questions for missing critical attributes."""
    questions = []
    s_name = supplier.raw_name
    s_art = supplier.article_number or "N/A"

    for missing in evidence.missing_critical:
        attr = missing.attribute_name
        question = _format_question(attr, s_name, s_art, hospital)
        if question:
            questions.append({
                "attribute_name": attr,
                "question_text": question,
            })

    return questions


def _format_question(
    attr: str, product_name: str, article_number: str, hospital: HospitalArticle
) -> str:
    """Format a specific supplier question based on the missing attribute."""
    templates = {
        "sterility": (
            f'Is product "{product_name}" (Art.-Nr. {article_number}) supplied sterile? '
            f"If yes, please specify the sterilization method and provide the relevant "
            f"documentation or certification."
        ),
        "material": (
            f'What is the primary material of "{product_name}" (Art.-Nr. {article_number})? '
            f"The hospital article specifies {hospital.material or 'a specific material'}. "
            f"Please provide the exact material composition."
        ),
        "mdr_class": (
            f'What is the MDR (Medical Device Regulation) risk classification of '
            f'"{product_name}" (Art.-Nr. {article_number})? '
            f"Please specify the class (I, IIa, IIb, or III) and provide the "
            f"relevant CE marking documentation."
        ),
        "connector_type": (
            f'What connector type does "{product_name}" (Art.-Nr. {article_number}) use? '
            f"The hospital requires {hospital.connector_type or 'a specific connector type'}. "
            f"Please specify: Luer, Luer-Lock, NRFit, or other."
        ),
        "size": (
            f'Please specify the exact dimensions/size of "{product_name}" '
            f"(Art.-Nr. {article_number}). "
            f"The hospital article specifies: {hospital.size_label or 'N/A'}."
        ),
        "product_category": (
            f'Please confirm the product category/type of "{product_name}" '
            f"(Art.-Nr. {article_number})."
        ),
    }

    return templates.get(attr, (
        f'Please provide the {attr} specification for "{product_name}" '
        f"(Art.-Nr. {article_number})."
    ))


def _attr_to_dict(a: AttributeComparison) -> dict:
    return {
        "attribute_name": a.attribute_name,
        "hospital_value": a.hospital_value,
        "supplier_value": a.supplier_value,
        "status": a.status,
        "criticality": a.criticality,
        "note": a.note,
    }


def _persist_comparison(
    db: Session,
    hospital: HospitalArticle,
    supplier: SupplierProduct,
    result: dict,
    evidence: ComparisonEvidence,
    candidate_rank: int,
    candidate_score: float,
):
    """Persist comparison result and evidence to database."""
    # Check for existing comparison
    existing = db.query(Comparison).filter_by(
        hospital_article_id=hospital.id,
        supplier_product_id=supplier.id,
    ).first()

    if existing:
        # Update existing
        existing.decision = result["decision"]
        existing.confidence = result["confidence"]
        existing.summary = result["summary"]
        existing.reasoning_summary = result["reasoning_summary"]
        existing.candidate_rank = candidate_rank
        existing.candidate_score = candidate_score
        existing.version += 1

        # Delete old evidence
        db.query(EvidenceModel).filter_by(comparison_id=existing.id).delete()

        # Delete old unanswered questions
        db.query(InformationRequest).filter_by(
            comparison_id=existing.id,
            status="open",
        ).delete()

        comparison = existing
    else:
        comparison = Comparison(
            hospital_article_id=hospital.id,
            supplier_product_id=supplier.id,
            decision=result["decision"],
            confidence=result["confidence"],
            summary=result["summary"],
            reasoning_summary=result["reasoning_summary"],
            candidate_rank=candidate_rank,
            candidate_score=candidate_score,
        )
        db.add(comparison)
        db.flush()  # Get ID

    # Add evidence
    for attr_comp in evidence.comparisons:
        ev = EvidenceModel(
            comparison_id=comparison.id,
            attribute_name=attr_comp.attribute_name,
            hospital_value=attr_comp.hospital_value,
            supplier_value=attr_comp.supplier_value,
            status=attr_comp.status,
            criticality=attr_comp.criticality,
            note=attr_comp.note,
        )
        db.add(ev)

    # Add information requests for missing critical attributes
    for q in result["supplier_questions"]:
        # Check if this question already exists (even from previous version)
        existing_q = db.query(InformationRequest).filter_by(
            supplier_product_id=supplier.id,
            attribute_name=q["attribute_name"],
        ).first()

        if not existing_q:
            req = InformationRequest(
                comparison_id=comparison.id,
                supplier_product_id=supplier.id,
                attribute_name=q["attribute_name"],
                question_text=q["question_text"],
                status="open",
            )
            db.add(req)

    db.commit()
