"""
Enrichment service: handles the supplier Q&A workflow.

When a supplier answers a question:
1. Stores the answer as an InformationResponse
2. Updates the SupplierProduct attribute with provenance tracking
3. Creates an EnrichmentEvent for audit trail
4. Re-runs the comparison automatically
5. Returns the updated comparison result
"""

from sqlalchemy.orm import Session
from backend.app.models import (
    InformationRequest, InformationResponse, SupplierProduct,
    EnrichmentEvent, HospitalArticle,
)
from backend.app.comparison.decision_engine import run_comparison


# Mapping from attribute names to SupplierProduct column names
ATTRIBUTE_COLUMN_MAP = {
    "sterility": "sterility",
    "material": "material",
    "mdr_class": "mdr_class",
    "connector_type": "connector_type",
    "size": "size_label",
    "product_category": "product_category",
}

# Mapping from answer text to normalized values
STERILITY_ANSWERS = {
    "sterile": "sterile",
    "steril": "sterile",
    "yes": "sterile",
    "ja": "sterile",
    "non-sterile": "non-sterile",
    "nicht steril": "non-sterile",
    "no": "non-sterile",
    "nein": "non-sterile",
    "unsteril": "non-sterile",
}

MDR_CLASS_ANSWERS = {
    "i": "I",
    "1": "I",
    "iia": "IIa",
    "2a": "IIa",
    "iib": "IIb",
    "2b": "IIb",
    "iii": "III",
    "3": "III",
}


def process_answer(
    db: Session,
    request_id: int,
    answer_text: str,
    answered_by: str = "Supplier",
) -> dict:
    """
    Process a supplier's answer to an information request.

    Returns the updated comparison result after re-evaluation.
    """
    # 1. Get the request
    request = db.query(InformationRequest).filter_by(id=request_id).first()
    if not request:
        raise ValueError(f"Information request {request_id} not found")

    if request.status == "answered":
        raise ValueError(f"Information request {request_id} already answered")

    # 2. Store the response
    response = InformationResponse(
        request_id=request.id,
        answer_text=answer_text,
        answered_by=answered_by,
    )
    db.add(response)

    # 3. Update request status
    request.status = "answered"

    # 4. Normalize the answer and update supplier product
    supplier_product = db.query(SupplierProduct).filter_by(
        id=request.supplier_product_id
    ).first()

    if supplier_product:
        column_name = ATTRIBUTE_COLUMN_MAP.get(request.attribute_name)
        if column_name:
            old_value = getattr(supplier_product, column_name, None)
            normalized_value = _normalize_answer(request.attribute_name, answer_text)

            # Update the attribute
            setattr(supplier_product, column_name, normalized_value)

            # Update provenance
            supplier_product.set_provenance(
                request.attribute_name,
                source="supplier_response",
                confidence=1.0,
            )

            # 5. Create enrichment event
            event = EnrichmentEvent(
                supplier_product_id=supplier_product.id,
                attribute_name=request.attribute_name,
                old_value=str(old_value) if old_value else None,
                new_value=normalized_value,
                source="supplier_response",
                confidence=1.0,
                triggered_by_request_id=request.id,
            )
            db.add(event)

    db.commit()

    # 6. Re-run comparison
    hospital_article = db.query(HospitalArticle).filter_by(
        id=request.comparison.hospital_article_id
    ).first()

    if hospital_article and supplier_product:
        result = run_comparison(
            hospital=hospital_article,
            supplier=supplier_product,
            candidate_rank=request.comparison.candidate_rank or 0,
            candidate_score=request.comparison.candidate_score or 0.0,
            db=db,
        )
        return result

    return {"status": "answer_stored", "re_comparison": "skipped"}


def _normalize_answer(attribute_name: str, answer: str) -> str:
    """Normalize a supplier's free-text answer to a canonical value."""
    answer_lower = answer.strip().lower()

    if attribute_name == "sterility":
        return STERILITY_ANSWERS.get(answer_lower, answer.strip())

    if attribute_name == "mdr_class":
        return MDR_CLASS_ANSWERS.get(answer_lower, answer.strip().upper())

    # For other attributes, return cleaned value
    return answer.strip()
