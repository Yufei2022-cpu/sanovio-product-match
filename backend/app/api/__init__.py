"""
FastAPI application and API routes for the SANOVIO Product Match system.
"""

import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from contextlib import asynccontextmanager

from backend.app.db import get_db, init_db, reset_db, engine
from backend.app.models import (
    Base, HospitalArticle, SupplierProduct, Supplier, Comparison,
    ComparisonEvidence, InformationRequest, InformationResponse,
)
from backend.app.schemas import (
    HospitalArticleOut, SupplierProductOut, ComparisonResultOut,
    ComparisonSummaryOut, AttributeComparisonOut, InformationRequestOut,
    InformationResponseOut, AnswerSubmission, DashboardStats,
    Decision, MatchStatus, Criticality,
)
from backend.app.ingestion.hospital_importer import (
    import_hospital_articles_from_tsv, get_sample_hospital_data,
)
from backend.app.ingestion.supplier_seeder import seed_suppliers, seed_supplier_products
from backend.app.matching.candidate_generator import generate_candidates
from backend.app.comparison.decision_engine import run_comparison
from backend.app.enrichment import process_answer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed sample data on startup."""
    Base.metadata.create_all(bind=engine)
    from backend.app.db import get_db_session
    with get_db_session() as db:
        # Check if data already exists
        article_count = db.query(HospitalArticle).count()
        if article_count == 0:
            # Seed hospital articles
            tsv = get_sample_hospital_data()
            import_hospital_articles_from_tsv(tsv, db)
            # Seed suppliers and products
            seed_suppliers(db)
            seed_supplier_products(db)
            print("[OK] Sample data seeded successfully")
        else:
            print(f"[INFO] Database already has {article_count} hospital articles")
    yield


app = FastAPI(
    title="SANOVIO Product Match",
    description="Hospital-supplier product replacement matching system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    """Get overview statistics."""
    return DashboardStats(
        total_hospital_articles=db.query(HospitalArticle).count(),
        total_supplier_products=db.query(SupplierProduct).count(),
        total_comparisons=db.query(Comparison).count(),
        compatible_count=db.query(Comparison).filter_by(decision="compatible").count(),
        incompatible_count=db.query(Comparison).filter_by(decision="incompatible").count(),
        uncertain_count=db.query(Comparison).filter_by(decision="uncertain").count(),
        open_questions=db.query(InformationRequest).filter_by(status="open").count(),
        answered_questions=db.query(InformationRequest).filter_by(status="answered").count(),
    )


# ---------------------------------------------------------------------------
# Hospital Articles
# ---------------------------------------------------------------------------

@app.get("/api/articles", response_model=list[HospitalArticleOut])
def list_articles(db: Session = Depends(get_db)):
    """List all hospital articles with comparison summary counts."""
    articles = db.query(HospitalArticle).all()
    result = []
    for a in articles:
        out = HospitalArticleOut.model_validate(a)
        out.dimensions = a.dimensions
        # Count comparisons
        out.compatible_count = db.query(Comparison).filter_by(
            hospital_article_id=a.id, decision="compatible"
        ).count()
        out.uncertain_count = db.query(Comparison).filter_by(
            hospital_article_id=a.id, decision="uncertain"
        ).count()
        out.incompatible_count = db.query(Comparison).filter_by(
            hospital_article_id=a.id, decision="incompatible"
        ).count()
        result.append(out)
    return result


@app.get("/api/articles/{article_id}", response_model=HospitalArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single hospital article."""
    article = db.query(HospitalArticle).filter_by(id=article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    out = HospitalArticleOut.model_validate(article)
    out.dimensions = article.dimensions
    out.compatible_count = db.query(Comparison).filter_by(
        hospital_article_id=article.id, decision="compatible"
    ).count()
    out.uncertain_count = db.query(Comparison).filter_by(
        hospital_article_id=article.id, decision="uncertain"
    ).count()
    out.incompatible_count = db.query(Comparison).filter_by(
        hospital_article_id=article.id, decision="incompatible"
    ).count()
    return out


@app.get("/api/articles/{article_id}/comparisons", response_model=list[ComparisonSummaryOut])
def get_article_comparisons(article_id: int, db: Session = Depends(get_db)):
    """Get all comparisons for a hospital article, ranked."""
    comparisons = (
        db.query(Comparison)
        .filter_by(hospital_article_id=article_id)
        .order_by(Comparison.candidate_rank.asc())
        .all()
    )
    results = []
    for c in comparisons:
        sp = db.query(SupplierProduct).filter_by(id=c.supplier_product_id).first()
        supplier = db.query(Supplier).filter_by(id=sp.supplier_id).first() if sp else None
        open_q = db.query(InformationRequest).filter_by(
            comparison_id=c.id, status="open"
        ).count()
        results.append(ComparisonSummaryOut(
            id=c.id,
            supplier_product_id=c.supplier_product_id,
            supplier_name=supplier.name if supplier else None,
            supplier_product_name=sp.raw_name if sp else "Unknown",
            decision=Decision(c.decision),
            confidence=c.confidence,
            candidate_rank=c.candidate_rank,
            summary=c.summary,
            open_questions=open_q,
        ))
    return results


# ---------------------------------------------------------------------------
# Supplier Products
# ---------------------------------------------------------------------------

@app.get("/api/supplier-products", response_model=list[SupplierProductOut])
def list_supplier_products(db: Session = Depends(get_db)):
    """List all supplier products."""
    products = db.query(SupplierProduct).all()
    results = []
    for p in products:
        out = SupplierProductOut.model_validate(p)
        out.dimensions = p.dimensions
        supplier = db.query(Supplier).filter_by(id=p.supplier_id).first()
        out.supplier_name = supplier.name if supplier else None
        if p.din_iso_norms:
            try:
                out.din_iso_norms = json.loads(p.din_iso_norms)
            except (json.JSONDecodeError, TypeError):
                out.din_iso_norms = []
        results.append(out)
    return results


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------

@app.post("/api/comparisons/run")
def run_all_comparisons(db: Session = Depends(get_db)):
    """Run comparisons for all hospital articles against all supplier products."""
    articles = db.query(HospitalArticle).all()
    supplier_products = db.query(SupplierProduct).all()

    total_comparisons = 0
    for article in articles:
        # Generate candidates
        candidates = generate_candidates(article, supplier_products, top_k=5)

        for candidate in candidates:
            sp = db.query(SupplierProduct).filter_by(id=candidate.supplier_product_id).first()
            if sp:
                run_comparison(
                    hospital=article,
                    supplier=sp,
                    candidate_rank=candidate.rank,
                    candidate_score=candidate.score,
                    db=db,
                )
                total_comparisons += 1

    return {
        "status": "completed",
        "total_comparisons": total_comparisons,
        "articles_processed": len(articles),
    }


@app.get("/api/comparisons/{comparison_id}", response_model=ComparisonResultOut)
def get_comparison(comparison_id: int, db: Session = Depends(get_db)):
    """Get detailed comparison result with evidence."""
    comparison = db.query(Comparison).filter_by(id=comparison_id).first()
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    # Get evidence
    evidence = db.query(ComparisonEvidence).filter_by(
        comparison_id=comparison.id
    ).all()

    # Get questions
    questions = db.query(InformationRequest).filter_by(
        comparison_id=comparison.id
    ).all()

    # Get related entities
    hospital = db.query(HospitalArticle).filter_by(
        id=comparison.hospital_article_id
    ).first()
    supplier_product = db.query(SupplierProduct).filter_by(
        id=comparison.supplier_product_id
    ).first()
    supplier = db.query(Supplier).filter_by(
        id=supplier_product.supplier_id
    ).first() if supplier_product else None

    # Build response
    all_evidence = []
    matching = []
    conflicting = []
    missing_critical = []

    for ev in evidence:
        attr_out = AttributeComparisonOut(
            attribute_name=ev.attribute_name,
            hospital_value=ev.hospital_value,
            supplier_value=ev.supplier_value,
            status=MatchStatus(ev.status),
            criticality=Criticality(ev.criticality),
            note=ev.note,
        )
        all_evidence.append(attr_out)
        if ev.status == "match":
            matching.append(attr_out)
        elif ev.status == "conflict":
            conflicting.append(attr_out)
        elif ev.status == "missing" and ev.criticality in ("hard_blocker", "critical"):
            missing_critical.append(attr_out)

    # Build question outputs
    question_outs = []
    for q in questions:
        resp = db.query(InformationResponse).filter_by(request_id=q.id).first()
        q_out = InformationRequestOut(
            id=q.id,
            comparison_id=q.comparison_id,
            supplier_product_id=q.supplier_product_id,
            attribute_name=q.attribute_name,
            question_text=q.question_text,
            status=q.status,
            hospital_article_name=hospital.raw_name if hospital else None,
            supplier_product_name=supplier_product.raw_name if supplier_product else None,
            response=InformationResponseOut(
                id=resp.id,
                request_id=resp.request_id,
                answer_text=resp.answer_text,
                answered_by=resp.answered_by,
                answered_at=str(resp.answered_at) if resp.answered_at else None,
            ) if resp else None,
        )
        question_outs.append(q_out)

    # Build article/product outputs
    h_out = HospitalArticleOut.model_validate(hospital) if hospital else None
    if h_out and hospital:
        h_out.dimensions = hospital.dimensions

    sp_out = SupplierProductOut.model_validate(supplier_product) if supplier_product else None
    if sp_out and supplier_product:
        sp_out.dimensions = supplier_product.dimensions
        sp_out.supplier_name = supplier.name if supplier else None
        if supplier_product.din_iso_norms:
            try:
                sp_out.din_iso_norms = json.loads(supplier_product.din_iso_norms)
            except (json.JSONDecodeError, TypeError):
                sp_out.din_iso_norms = []

    return ComparisonResultOut(
        id=comparison.id,
        hospital_article_id=comparison.hospital_article_id,
        supplier_product_id=comparison.supplier_product_id,
        decision=Decision(comparison.decision),
        confidence=comparison.confidence,
        summary=comparison.summary,
        reasoning_summary=comparison.reasoning_summary,
        candidate_rank=comparison.candidate_rank,
        candidate_score=comparison.candidate_score,
        version=comparison.version,
        matching_attributes=matching,
        conflicting_attributes=conflicting,
        missing_critical_attributes=missing_critical,
        all_evidence=all_evidence,
        supplier_questions=question_outs,
        hospital_article=h_out,
        supplier_product=sp_out,
    )


# ---------------------------------------------------------------------------
# Information Requests (Supplier Q&A)
# ---------------------------------------------------------------------------

@app.get("/api/questions", response_model=list[InformationRequestOut])
def list_questions(status: str = None, db: Session = Depends(get_db)):
    """List information requests, optionally filtered by status."""
    query = db.query(InformationRequest)
    if status:
        query = query.filter_by(status=status)
    requests = query.all()

    results = []
    for q in requests:
        sp = db.query(SupplierProduct).filter_by(id=q.supplier_product_id).first()
        comparison = db.query(Comparison).filter_by(id=q.comparison_id).first()
        hospital = db.query(HospitalArticle).filter_by(
            id=comparison.hospital_article_id
        ).first() if comparison else None

        resp = db.query(InformationResponse).filter_by(request_id=q.id).first()

        results.append(InformationRequestOut(
            id=q.id,
            comparison_id=q.comparison_id,
            supplier_product_id=q.supplier_product_id,
            attribute_name=q.attribute_name,
            question_text=q.question_text,
            status=q.status,
            hospital_article_name=hospital.raw_name if hospital else None,
            supplier_product_name=sp.raw_name if sp else None,
            response=InformationResponseOut(
                id=resp.id,
                request_id=resp.request_id,
                answer_text=resp.answer_text,
                answered_by=resp.answered_by,
                answered_at=str(resp.answered_at) if resp.answered_at else None,
            ) if resp else None,
        ))

    return results


@app.post("/api/questions/{question_id}/answer")
def answer_question(
    question_id: int,
    submission: AnswerSubmission,
    db: Session = Depends(get_db),
):
    """
    Supplier submits an answer to an information request.
    The system stores the answer, enriches the product, and re-runs comparison.
    """
    try:
        result = process_answer(
            db=db,
            request_id=question_id,
            answer_text=submission.answer_text,
            answered_by=submission.answered_by or "Supplier",
        )
        return {"status": "success", "updated_comparison": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Data Management
# ---------------------------------------------------------------------------

@app.post("/api/reset")
def reset_data(db: Session = Depends(get_db)):
    """Reset database and re-seed sample data (development only)."""
    reset_db()
    from backend.app.db import get_db_session
    with get_db_session() as fresh_db:
        tsv = get_sample_hospital_data()
        import_hospital_articles_from_tsv(tsv, fresh_db)
        seed_suppliers(fresh_db)
        seed_supplier_products(fresh_db)
    return {"status": "reset_complete"}
