"""
SQLAlchemy ORM models for the SANOVIO Product Match system.

Design decisions:
- HospitalArticle and SupplierProduct share a common attribute structure
  but are separate tables (different provenance, different import paths).
- Comparison stores the full decision + evidence for audit trail.
- InformationRequest/Response enable the supplier enrichment workflow.
- EnrichmentEvent provides provenance tracking for attribute changes.
"""

import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum, Boolean
)
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ComparisonDecision(str, enum.Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNCERTAIN = "uncertain"


class AttributeMatchStatus(str, enum.Enum):
    MATCH = "match"
    CONFLICT = "conflict"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class AttributeCriticality(str, enum.Enum):
    HARD_BLOCKER = "hard_blocker"
    CRITICAL = "critical"
    IMPORTANT = "important"
    INFORMATIONAL = "informational"


class QuestionStatus(str, enum.Enum):
    OPEN = "open"
    ANSWERED = "answered"
    DISMISSED = "dismissed"


class AttributeSource(str, enum.Enum):
    HOSPITAL_MASTER = "hospital_master"
    SUPPLIER_CATALOG = "supplier_catalog"
    SUPPLIER_RESPONSE = "supplier_response"
    LLM_EXTRACTED = "llm_extracted"
    SYNTHETIC = "synthetic"


# ---------------------------------------------------------------------------
# Hospital Article
# ---------------------------------------------------------------------------

class HospitalArticle(Base):
    __tablename__ = "hospital_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    internal_id = Column(String, unique=True, nullable=False)
    raw_name = Column(Text, nullable=False)  # Artikelbezeichnung
    brand = Column(String, nullable=True)  # Marke
    article_number = Column(String, nullable=True)  # Artikelnummer
    annual_quantity = Column(Integer, nullable=True)  # Jahresmenge
    order_unit = Column(String, nullable=True)  # Bestellmengeneinheit
    base_units_per_order_unit = Column(Integer, nullable=True)
    base_unit = Column(String, nullable=True)  # Basismengeneinheit
    gtin = Column(String, nullable=True)
    ean = Column(String, nullable=True)
    mdr_class = Column(String, nullable=True)  # MDR-Klasse
    net_target_price = Column(Float, nullable=True)  # Netto-Zielpreis
    currency = Column(String, nullable=True)

    # Extracted / normalized attributes (from free-text parsing)
    product_category = Column(String, nullable=True)
    product_subcategory = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    material = Column(String, nullable=True)
    sterility = Column(String, nullable=True)  # "sterile" | "non-sterile" | null
    size_label = Column(String, nullable=True)  # e.g. "10 ml", "M", "0.8 x 40 mm"
    dimensions_json = Column(Text, nullable=True)  # JSON: {"volume_ml": 10} etc.
    connector_type = Column(String, nullable=True)  # luer, luer-lock, nrfit
    graduation_ml = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    comparisons = relationship("Comparison", back_populates="hospital_article")

    @property
    def dimensions(self) -> dict | None:
        if self.dimensions_json:
            return json.loads(self.dimensions_json)
        return None

    @dimensions.setter
    def dimensions(self, value: dict | None):
        self.dimensions_json = json.dumps(value) if value else None


# ---------------------------------------------------------------------------
# Supplier & Supplier Product
# ---------------------------------------------------------------------------

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)

    products = relationship("SupplierProduct", back_populates="supplier")


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    raw_name = Column(Text, nullable=False)
    article_number = Column(String, nullable=True)
    brand = Column(String, nullable=True)

    # Identifiers
    gtin = Column(String, nullable=True)
    ean = Column(String, nullable=True)
    pzn = Column(String, nullable=True)
    himiv = Column(String, nullable=True)

    # Normalized attributes
    product_category = Column(String, nullable=True)
    product_subcategory = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    material = Column(String, nullable=True)
    sterility = Column(String, nullable=True)
    size_label = Column(String, nullable=True)
    dimensions_json = Column(Text, nullable=True)
    connector_type = Column(String, nullable=True)
    graduation_ml = Column(Float, nullable=True)

    # Packaging
    packaging_unit = Column(String, nullable=True)
    units_per_package = Column(Integer, nullable=True)
    base_unit = Column(String, nullable=True)

    # Regulatory
    mdr_class = Column(String, nullable=True)
    din_iso_norms = Column(Text, nullable=True)  # JSON array

    # Pricing (rare in catalogs)
    price_per_unit = Column(Float, nullable=True)
    currency = Column(String, nullable=True)

    # Provenance tracking (JSON: attr_name -> {source, confidence})
    provenance_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    comparisons = relationship("Comparison", back_populates="supplier_product")
    information_requests = relationship("InformationRequest", back_populates="supplier_product")
    enrichment_events = relationship("EnrichmentEvent", back_populates="supplier_product")

    @property
    def dimensions(self) -> dict | None:
        if self.dimensions_json:
            return json.loads(self.dimensions_json)
        return None

    @dimensions.setter
    def dimensions(self, value: dict | None):
        self.dimensions_json = json.dumps(value) if value else None

    def get_provenance(self, attr_name: str) -> dict | None:
        if self.provenance_json:
            prov = json.loads(self.provenance_json)
            return prov.get(attr_name)
        return None

    def set_provenance(self, attr_name: str, source: str, confidence: float = 1.0):
        prov = json.loads(self.provenance_json) if self.provenance_json else {}
        prov[attr_name] = {"source": source, "confidence": confidence}
        self.provenance_json = json.dumps(prov)


# ---------------------------------------------------------------------------
# Comparison & Evidence
# ---------------------------------------------------------------------------

class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_article_id = Column(Integer, ForeignKey("hospital_articles.id"), nullable=False)
    supplier_product_id = Column(Integer, ForeignKey("supplier_products.id"), nullable=False)

    decision = Column(String, nullable=False)  # compatible | incompatible | uncertain
    confidence = Column(Float, nullable=False, default=0.0)
    summary = Column(Text, nullable=True)
    reasoning_summary = Column(Text, nullable=True)

    # Candidate generation metadata
    candidate_rank = Column(Integer, nullable=True)
    candidate_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    version = Column(Integer, default=1)  # Incremented on re-evaluation

    # Relationships
    hospital_article = relationship("HospitalArticle", back_populates="comparisons")
    supplier_product = relationship("SupplierProduct", back_populates="comparisons")
    evidence = relationship("ComparisonEvidence", back_populates="comparison",
                            cascade="all, delete-orphan")
    information_requests = relationship("InformationRequest", back_populates="comparison")


class ComparisonEvidence(Base):
    __tablename__ = "comparison_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comparison_id = Column(Integer, ForeignKey("comparisons.id"), nullable=False)

    attribute_name = Column(String, nullable=False)  # e.g. "sterility", "size"
    hospital_value = Column(String, nullable=True)
    supplier_value = Column(String, nullable=True)
    status = Column(String, nullable=False)  # match | conflict | missing
    criticality = Column(String, nullable=False)  # hard_blocker | critical | important | informational
    note = Column(Text, nullable=True)

    comparison = relationship("Comparison", back_populates="evidence")


# ---------------------------------------------------------------------------
# Information Request / Response (Supplier Q&A)
# ---------------------------------------------------------------------------

class InformationRequest(Base):
    __tablename__ = "information_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comparison_id = Column(Integer, ForeignKey("comparisons.id"), nullable=False)
    supplier_product_id = Column(Integer, ForeignKey("supplier_products.id"), nullable=False)

    attribute_name = Column(String, nullable=False)  # Which attribute is missing
    question_text = Column(Text, nullable=False)  # Human-readable question
    status = Column(String, default="open")  # open | answered | dismissed

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    comparison = relationship("Comparison", back_populates="information_requests")
    supplier_product = relationship("SupplierProduct", back_populates="information_requests")
    response = relationship("InformationResponse", back_populates="request", uselist=False)


class InformationResponse(Base):
    __tablename__ = "information_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("information_requests.id"), nullable=False)

    answer_text = Column(Text, nullable=False)
    answered_by = Column(String, nullable=True)  # e.g., supplier contact name
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    request = relationship("InformationRequest", back_populates="response")


# ---------------------------------------------------------------------------
# Enrichment Event (Provenance Audit Trail)
# ---------------------------------------------------------------------------

class EnrichmentEvent(Base):
    __tablename__ = "enrichment_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_product_id = Column(Integer, ForeignKey("supplier_products.id"), nullable=False)

    attribute_name = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=False)
    source = Column(String, nullable=False)  # supplier_response | llm_extracted | manual
    confidence = Column(Float, default=1.0)
    triggered_by_request_id = Column(Integer, ForeignKey("information_requests.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    supplier_product = relationship("SupplierProduct", back_populates="enrichment_events")
