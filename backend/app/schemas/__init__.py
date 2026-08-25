"""
Pydantic schemas for API request/response models and internal data transfer.
"""

from __future__ import annotations
import json
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Enums (mirroring SQLAlchemy enums for API layer)
# ---------------------------------------------------------------------------

class Decision(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNCERTAIN = "uncertain"


class MatchStatus(str, Enum):
    MATCH = "match"
    CONFLICT = "conflict"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class Criticality(str, Enum):
    HARD_BLOCKER = "hard_blocker"
    CRITICAL = "critical"
    IMPORTANT = "important"
    INFORMATIONAL = "informational"


# ---------------------------------------------------------------------------
# Attribute Provenance
# ---------------------------------------------------------------------------

class AttributeProvenance(BaseModel):
    value: Optional[str] = None
    source: str  # hospital_master | supplier_catalog | supplier_response | llm_extracted
    confidence: float = 1.0
    extracted_from: Optional[str] = None


# ---------------------------------------------------------------------------
# Product Schemas
# ---------------------------------------------------------------------------

class HospitalArticleOut(BaseModel):
    id: int
    internal_id: str
    raw_name: str
    brand: Optional[str] = None
    article_number: Optional[str] = None
    annual_quantity: Optional[int] = None
    order_unit: Optional[str] = None
    base_units_per_order_unit: Optional[int] = None
    base_unit: Optional[str] = None
    gtin: Optional[str] = None
    ean: Optional[str] = None
    mdr_class: Optional[str] = None
    net_target_price: Optional[float] = None
    currency: Optional[str] = None
    product_category: Optional[str] = None
    product_subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    material: Optional[str] = None
    sterility: Optional[str] = None
    size_label: Optional[str] = None
    dimensions: Optional[dict] = None
    connector_type: Optional[str] = None
    graduation_ml: Optional[float] = None

    # Aggregated match info (populated by API)
    compatible_count: int = 0
    uncertain_count: int = 0
    incompatible_count: int = 0

    model_config = {"from_attributes": True}


class SupplierProductOut(BaseModel):
    id: int
    supplier_id: int
    supplier_name: Optional[str] = None
    raw_name: str
    article_number: Optional[str] = None
    brand: Optional[str] = None
    gtin: Optional[str] = None
    ean: Optional[str] = None
    pzn: Optional[str] = None
    himiv: Optional[str] = None
    product_category: Optional[str] = None
    product_subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    material: Optional[str] = None
    sterility: Optional[str] = None
    size_label: Optional[str] = None
    dimensions: Optional[dict] = None
    connector_type: Optional[str] = None
    graduation_ml: Optional[float] = None
    packaging_unit: Optional[str] = None
    units_per_package: Optional[int] = None
    base_unit: Optional[str] = None
    mdr_class: Optional[str] = None
    din_iso_norms: Optional[list[str]] = None
    price_per_unit: Optional[float] = None
    currency: Optional[str] = None

    @field_validator("din_iso_norms", mode="before")
    @classmethod
    def parse_din_iso_norms(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v] if v else []
        return v

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Comparison Schemas
# ---------------------------------------------------------------------------

class AttributeComparisonOut(BaseModel):
    attribute_name: str
    hospital_value: Optional[str] = None
    supplier_value: Optional[str] = None
    status: MatchStatus
    criticality: Criticality
    note: Optional[str] = None


class ComparisonResultOut(BaseModel):
    id: int
    hospital_article_id: int
    supplier_product_id: int
    decision: Decision
    confidence: float
    summary: Optional[str] = None
    reasoning_summary: Optional[str] = None
    candidate_rank: Optional[int] = None
    candidate_score: Optional[float] = None
    version: int = 1

    matching_attributes: list[AttributeComparisonOut] = []
    conflicting_attributes: list[AttributeComparisonOut] = []
    missing_critical_attributes: list[AttributeComparisonOut] = []
    all_evidence: list[AttributeComparisonOut] = []

    supplier_questions: list[InformationRequestOut] = []

    hospital_article: Optional[HospitalArticleOut] = None
    supplier_product: Optional[SupplierProductOut] = None

    model_config = {"from_attributes": True}


class ComparisonSummaryOut(BaseModel):
    """Lightweight comparison for listing."""
    id: int
    supplier_product_id: int
    supplier_name: Optional[str] = None
    supplier_product_name: str
    decision: Decision
    confidence: float
    candidate_rank: Optional[int] = None
    summary: Optional[str] = None
    open_questions: int = 0


# ---------------------------------------------------------------------------
# Information Request / Response Schemas
# ---------------------------------------------------------------------------

class InformationRequestOut(BaseModel):
    id: int
    comparison_id: int
    supplier_product_id: int
    attribute_name: str
    question_text: str
    status: str
    hospital_article_name: Optional[str] = None
    supplier_product_name: Optional[str] = None
    response: Optional[InformationResponseOut] = None

    model_config = {"from_attributes": True}


class InformationResponseOut(BaseModel):
    id: int
    request_id: int
    answer_text: str
    answered_by: Optional[str] = None
    answered_at: Optional[str] = None

    model_config = {"from_attributes": True}


class AnswerSubmission(BaseModel):
    """Request body for supplier answering a question."""
    answer_text: str
    answered_by: Optional[str] = "Supplier"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_hospital_articles: int = 0
    total_supplier_products: int = 0
    total_comparisons: int = 0
    compatible_count: int = 0
    incompatible_count: int = 0
    uncertain_count: int = 0
    open_questions: int = 0
    answered_questions: int = 0


# Fix forward reference
InformationRequestOut.model_rebuild()
