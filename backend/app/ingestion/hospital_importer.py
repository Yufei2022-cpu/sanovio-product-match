"""
Hospital article importer: parses TSV/Excel hospital master data
into HospitalArticle ORM objects with extracted/normalized attributes.
"""

import csv
import io
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.models import HospitalArticle
from backend.app.ingestion.normalizer import (
    clean_gtin, normalize_unit, classify_product_category,
    extract_sterility, extract_connector_type, extract_material,
    extract_size_label, parse_dimensions,
)


def import_hospital_articles_from_tsv(tsv_content: str, db: Session) -> list[HospitalArticle]:
    """
    Parse tab-separated hospital article data and create HospitalArticle records.

    Handles:
    - GTIN/EAN apostrophe cleaning
    - Unit normalization
    - Attribute extraction from Artikelbezeichnung (category, sterility, material, size, connector)
    """
    articles = []
    reader = csv.DictReader(io.StringIO(tsv_content), delimiter="\t")

    for row in reader:
        raw_name = row.get("Artikelbezeichnung", "").strip()
        brand = row.get("Marke", "").strip() or None

        # Clean GTIN/EAN
        gtin = clean_gtin(row.get("GTIN", ""))
        ean = clean_gtin(row.get("EAN", ""))

        # Normalize units
        order_unit = normalize_unit(row.get("Bestellmengeneinheit", ""))
        base_unit = normalize_unit(row.get("Basismengeneinheit", ""))

        # Extract normalized attributes from product name
        category = classify_product_category(raw_name)
        sterility = extract_sterility(raw_name)
        connector = extract_connector_type(raw_name)
        material = extract_material(raw_name)
        size_label = extract_size_label(raw_name, category)
        dimensions = parse_dimensions(raw_name, category)

        # Parse numeric fields safely
        try:
            annual_qty = int(row.get("Jahresmenge", 0))
        except (ValueError, TypeError):
            annual_qty = None

        try:
            base_per_order = int(row.get("Basismengeneinheiten pro BME", 0))
        except (ValueError, TypeError):
            base_per_order = None

        try:
            price = float(row.get("Netto-Zielpreis", 0))
        except (ValueError, TypeError):
            price = None

        article = HospitalArticle(
            internal_id=row.get("internal_id", "").strip(),
            raw_name=raw_name,
            brand=brand,
            article_number=row.get("Artikelnummer", "").strip() or None,
            annual_quantity=annual_qty,
            order_unit=order_unit,
            base_units_per_order_unit=base_per_order,
            base_unit=base_unit,
            gtin=gtin,
            ean=ean,
            mdr_class=row.get("MDR-Klasse", "").strip() or None,
            net_target_price=price,
            currency=row.get("Währung", "").strip() or None,
            product_category=category,
            manufacturer=brand,  # Brand often equals manufacturer in hospital master
            material=material,
            sterility=sterility,
            size_label=size_label,
            connector_type=connector,
        )

        if dimensions:
            article.dimensions = dimensions

        articles.append(article)

    # Persist
    for article in articles:
        existing = db.query(HospitalArticle).filter_by(
            internal_id=article.internal_id
        ).first()
        if not existing:
            db.add(article)
        else:
            # Update existing
            for attr in ["raw_name", "brand", "article_number", "gtin", "ean",
                         "mdr_class", "product_category", "sterility", "material",
                         "size_label", "connector_type", "manufacturer",
                         "net_target_price", "currency", "annual_quantity",
                         "order_unit", "base_units_per_order_unit", "base_unit"]:
                setattr(existing, attr, getattr(article, attr))
            if dimensions:
                existing.dimensions = dimensions

    db.commit()
    return articles


def get_sample_hospital_data() -> str:
    """Return the embedded sample hospital article TSV data."""
    return """internal_id\tArtikelbezeichnung\tMarke\tArtikelnummer\tJahresmenge\tBestellmengeneinheit\tBasismengeneinheiten pro BME\tBasismengeneinheit\tGTIN\tEAN\tMDR-Klasse\tNetto-Zielpreis\tWährung
1\tNitrilhandschuh Sensicare Ice blau L\tMedline\t486803\t4000\tBox\t200\tStück\t'04046719012345\t'4046719012348\tI\t0.019\tCHF
2\tVerbandstoff-Wundversorgung-Set steril\tHartmann\t4754183\t10000\tStk\t1\tStück\t'04046719098765\t'4046719098768\tIIa\t0.58\tCHF
3\tEinmalspritze 10 ml Luer-Lock steril\tB. Braun\t9154010\t15000\tPack\t100\tStück\t'04040456781234\t'4040456781237\tIIa\t0.12\tCHF
4\tInfusionsbesteck Intrafix Safe\tB. Braun\t4169125\t8500\tStk\t1\tStück\t'04040456783456\t'4040456783456\tIIa\t1.35\tCHF
5\tOP-Maske mit Bindebändern\tHartmann\t2912301\t22000\tBox\t50\tStück\t'04046719111223\t'4046719111226\tI\t0.08\tCHF
6\tKanüle Sterican 0,8 × 40 mm\tB. Braun\t4657689\t18000\tPack\t100\tStück\t'04040456999887\t'4040456999880\tIIa\t0.06\tCHF
7\tDesinfektionstücher Mikrozid AF\tSchülke\t70003456\t1200\tDose\t100\tTuch\t'04012345001234\t'4012345001237\tIIa\t3.95\tCHF
8\tEinmalhandschuh Latex puderfrei M\tAnsell\t9265432\t9000\tBox\t100\tStück\t'05010023456789\t'5010023456784\tI\t0.11\tCHF
9\tUrinbecher 100 ml steril\tSarstedt\t751345\t30000\tStk\t1\tStück\t'04012345678901\t'4012345678906\tI\t0.04\tCHF
10\tWundpflaster elastic 6 cm × 5 m\tHartmann\t9001234\t2500\tRolle\t1\tRolle\t'04046719222334\t'4046719222339\tI\t1.75\tCHF"""
