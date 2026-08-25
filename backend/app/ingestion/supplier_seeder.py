"""
Supplier product seeder: creates supplier products from
the B. Braun catalog extraction and synthetic data for other categories.

Design decision: Rather than building a complex PDF table parser for the
prototype, we manually structure the key products from the B. Braun catalog
text and add synthetic supplier data for categories not covered by the catalog
(gloves, masks, wound care, etc.) to demonstrate the full matching workflow.

In production, this would be replaced by a proper PDF extraction pipeline
(pdfplumber + layout analysis) or supplier-provided structured data feeds.
"""

import json
from sqlalchemy.orm import Session

from backend.app.models import Supplier, SupplierProduct


def seed_suppliers(db: Session) -> list[Supplier]:
    """Create supplier records."""
    suppliers_data = [
        {"name": "B. Braun Melsungen AG", "code": "BBRAUN"},
        {"name": "MedPro Healthcare Supplies", "code": "MEDPRO"},
        {"name": "HealthGuard Medical GmbH", "code": "HEALTHGUARD"},
    ]

    suppliers = []
    for s in suppliers_data:
        existing = db.query(Supplier).filter_by(code=s["code"]).first()
        if not existing:
            supplier = Supplier(**s)
            db.add(supplier)
            suppliers.append(supplier)
        else:
            suppliers.append(existing)

    db.commit()
    return suppliers


def seed_supplier_products(db: Session) -> list[SupplierProduct]:
    """Seed all supplier products (real catalog extraction + synthetic)."""
    suppliers = {s.code: s for s in db.query(Supplier).all()}

    if not suppliers:
        suppliers_list = seed_suppliers(db)
        suppliers = {s.code: s for s in suppliers_list}

    products = []

    # ---- B. Braun catalog products (extracted from the provided text) ----
    bbraun = suppliers["BBRAUN"]
    bbraun_products = _get_bbraun_catalog_products(bbraun.id)

    # ---- Synthetic supplier products (for demo completeness) ----
    medpro = suppliers["MEDPRO"]
    healthguard = suppliers["HEALTHGUARD"]
    synthetic_products = _get_synthetic_products(medpro.id, healthguard.id)

    all_products = bbraun_products + synthetic_products

    for prod_data in all_products:
        existing = db.query(SupplierProduct).filter_by(
            article_number=prod_data["article_number"],
            supplier_id=prod_data["supplier_id"],
        ).first()

        if not existing:
            prod = SupplierProduct(**prod_data)
            db.add(prod)
            products.append(prod)
        else:
            products.append(existing)

    db.commit()
    return products


def _get_bbraun_catalog_products(supplier_id: int) -> list[dict]:
    """
    Structured extraction from the B. Braun Einmalspritzen/Einmalkanülen catalog.
    Represents the output of PDF extraction → normalization.
    """
    base_prov = json.dumps({
        "raw_name": {"source": "supplier_catalog", "confidence": 1.0},
        "sterility": {"source": "supplier_catalog", "confidence": 0.95},
        "material": {"source": "supplier_catalog", "confidence": 0.9},
    })

    return [
        # --- Zweiteilige Einmalspritzen (Injekt®) ---
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Solo 2 ml",
            "article_number": "4606027V",
            "brand": "Injekt®",
            "pzn": "02057895",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "2 ml",
            "dimensions_json": json.dumps({"volume_ml": 2.0}),
            "connector_type": "luer",
            "graduation_ml": 0.1,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Solo 5 ml",
            "article_number": "4606051V",
            "brand": "Injekt®",
            "pzn": "02057903",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "5 ml",
            "dimensions_json": json.dumps({"volume_ml": 5.0}),
            "connector_type": "luer",
            "graduation_ml": 0.2,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Solo 10 ml",
            "article_number": "4606108N",
            "brand": "Injekt®",
            "pzn": "18074594",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "10 ml",
            "dimensions_json": json.dumps({"volume_ml": 10.0}),
            "connector_type": "luer",
            "graduation_ml": 0.5,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Solo 20 ml",
            "article_number": "4606205V",
            "brand": "Injekt®",
            "pzn": "02057932",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "20 ml",
            "dimensions_json": json.dumps({"volume_ml": 20.0}),
            "connector_type": "luer",
            "graduation_ml": 1.0,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },

        # --- Injekt® Luer Lock ---
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Lock Solo 2 ml",
            "article_number": "4606701V",
            "brand": "Injekt®",
            "pzn": "00610968",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "2 ml",
            "dimensions_json": json.dumps({"volume_ml": 2.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.1,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Lock Solo 5 ml",
            "article_number": "4606710V",
            "brand": "Injekt®",
            "pzn": "00610974",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "5 ml",
            "dimensions_json": json.dumps({"volume_ml": 5.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.2,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Lock Solo 10 ml",
            "article_number": "4606728V",
            "brand": "Injekt®",
            "pzn": "00611005",
            "himiv": "03.29.01.1052",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "10 ml",
            "dimensions_json": json.dumps({"volume_ml": 10.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.5,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Injekt® Luer Lock Solo 20 ml",
            "article_number": "4606736V",
            "brand": "Injekt®",
            "pzn": "00611034",
            "product_category": "syringe",
            "product_subcategory": "two_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "20 ml",
            "dimensions_json": json.dumps({"volume_ml": 20.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 1.0,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },

        # --- Dreiteilige Einmalspritzen (Omnifix®) Luer Lock ---
        {
            "supplier_id": supplier_id,
            "raw_name": "Omnifix® Luer Lock Solo 3 ml",
            "article_number": "4617022V",
            "brand": "Omnifix®",
            "pzn": "06706362",
            "product_category": "syringe",
            "product_subcategory": "three_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "3 ml",
            "dimensions_json": json.dumps({"volume_ml": 3.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.1,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Omnifix® Luer Lock Solo 5 ml",
            "article_number": "4617053V",
            "brand": "Omnifix®",
            "pzn": "00570016",
            "product_category": "syringe",
            "product_subcategory": "three_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "5 ml",
            "dimensions_json": json.dumps({"volume_ml": 5.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.2,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Omnifix® Luer Lock Solo 10 ml",
            "article_number": "4617100V",
            "brand": "Omnifix®",
            "pzn": "00570022",
            "himiv": "03.29.01.1065",
            "product_category": "syringe",
            "product_subcategory": "three_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "10 ml",
            "dimensions_json": json.dumps({"volume_ml": 10.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.5,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Omnifix® Luer Lock Solo 20 ml",
            "article_number": "4617207V",
            "brand": "Omnifix®",
            "pzn": "00570039",
            "product_category": "syringe",
            "product_subcategory": "three_part_luer_lock",
            "manufacturer": "B. Braun",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "20 ml",
            "dimensions_json": json.dumps({"volume_ml": 20.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 1.0,
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": base_prov,
        },

        # --- Sterican® Standard Needles ---
        {
            "supplier_id": supplier_id,
            "raw_name": "Sterican® 21 G × 1 ½\" (0,80 × 40 mm)",
            "article_number": "4657527B",
            "brand": "Sterican®",
            "pzn": "18746527",
            "product_category": "needle",
            "product_subcategory": "standard_injection",
            "manufacturer": "B. Braun",
            "material": "stainless_steel",
            "sterility": "sterile",
            "size_label": "0.80 × 40 mm",
            "dimensions_json": json.dumps({"od_mm": 0.80, "length_mm": 40.0, "gauge": "21G"}),
            "connector_type": "luer-lock",
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7864"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Sterican® 21 G × 1\" (0,80 × 25 mm)",
            "article_number": "4657543B",
            "brand": "Sterican®",
            "pzn": "18746510",
            "product_category": "needle",
            "product_subcategory": "standard_injection",
            "manufacturer": "B. Braun",
            "material": "stainless_steel",
            "sterility": "sterile",
            "size_label": "0.80 × 25 mm",
            "dimensions_json": json.dumps({"od_mm": 0.80, "length_mm": 25.0, "gauge": "21G"}),
            "connector_type": "luer-lock",
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7864"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Sterican® 20 G × 1 ½\" (0,90 × 40 mm)",
            "article_number": "4657519B",
            "brand": "Sterican®",
            "pzn": "18746591",
            "product_category": "needle",
            "product_subcategory": "standard_injection",
            "manufacturer": "B. Braun",
            "material": "stainless_steel",
            "sterility": "sterile",
            "size_label": "0.90 × 40 mm",
            "dimensions_json": json.dumps({"od_mm": 0.90, "length_mm": 40.0, "gauge": "20G"}),
            "connector_type": "luer-lock",
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7864"]),
            "provenance_json": base_prov,
        },
        {
            "supplier_id": supplier_id,
            "raw_name": "Sterican® 22 G × 1 ¼\" (0,70 × 30 mm)",
            "article_number": "4657624B",
            "brand": "Sterican®",
            "pzn": "18746473",
            "product_category": "needle",
            "product_subcategory": "standard_injection",
            "manufacturer": "B. Braun",
            "material": "stainless_steel",
            "sterility": "sterile",
            "size_label": "0.70 × 30 mm",
            "dimensions_json": json.dumps({"od_mm": 0.70, "length_mm": 30.0, "gauge": "22G"}),
            "connector_type": "luer-lock",
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7864"]),
            "provenance_json": base_prov,
        },

        # --- Sterican® Safety ---
        {
            "supplier_id": supplier_id,
            "raw_name": "Sterican® Safety 21 G × 1 ½\" (0,80 × 40 mm)",
            "article_number": "4670045S-01",
            "brand": "Sterican® Safety",
            "pzn": "13353906",
            "himiv": "03.99.99.1032",
            "product_category": "needle",
            "product_subcategory": "safety_injection",
            "manufacturer": "B. Braun",
            "material": "stainless_steel",
            "sterility": "sterile",
            "size_label": "0.80 × 40 mm",
            "dimensions_json": json.dumps({"od_mm": 0.80, "length_mm": 40.0, "gauge": "21G"}),
            "connector_type": "luer-lock",
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7864"]),
            "provenance_json": base_prov,
        },

        # --- Medibox® ---
        {
            "supplier_id": supplier_id,
            "raw_name": "Medibox® Abfallbehältnis 2,4 L",
            "article_number": "9193600",
            "brand": "Medibox®",
            "pzn": "13847399",
            "product_category": "sharps_container",
            "manufacturer": "B. Braun",
            "sterility": None,
            "size_label": "2.4 L",
            "dimensions_json": json.dumps({"volume_l": 2.4}),
            "packaging_unit": "Stück",
            "units_per_package": 27,
            "base_unit": "Stück",
            "provenance_json": base_prov,
        },
    ]


def _get_synthetic_products(medpro_id: int, healthguard_id: int) -> list[dict]:
    """
    Synthetic supplier products for categories NOT covered by B. Braun catalog.
    These enable demo of the full matching workflow across all 10 hospital articles.

    IMPORTANT: This is developer-created synthetic data, NOT real supplier data.
    Some products intentionally have missing attributes to demonstrate the
    UNCERTAIN → enrichment → re-evaluation workflow.
    """
    return [
        # --- Gloves (MedPro) ---
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Nitrile Examination Gloves Blue, Size L",
            "article_number": "MP-GL-NIT-L",
            "brand": "MedPro SafeHand",
            "product_category": "glove",
            "manufacturer": "MedPro Healthcare",
            "material": "nitrile",
            "sterility": "non-sterile",
            "size_label": "L",
            "mdr_class": "I",
            "packaging_unit": "Box",
            "units_per_package": 200,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 1.0},
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Nitrile Examination Gloves Blue, Size M",
            "article_number": "MP-GL-NIT-M",
            "brand": "MedPro SafeHand",
            "product_category": "glove",
            "manufacturer": "MedPro Healthcare",
            "material": "nitrile",
            "sterility": "non-sterile",
            "size_label": "M",
            "mdr_class": "I",
            "packaging_unit": "Box",
            "units_per_package": 200,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },
        {
            "supplier_id": healthguard_id,
            "raw_name": "HealthGuard Latex Untersuchungshandschuhe puderfrei M",
            "article_number": "HG-GL-LAT-M",
            "brand": "HealthGuard",
            "product_category": "glove",
            "manufacturer": "HealthGuard Medical",
            "material": "latex",
            "sterility": "non-sterile",
            "size_label": "M",
            "mdr_class": "I",
            "packaging_unit": "Box",
            "units_per_package": 100,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 1.0},
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Masks (MedPro) ---
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Surgical Mask Type II with Ties",
            "article_number": "MP-MASK-TIE",
            "brand": "MedPro",
            "product_category": "mask",
            "manufacturer": "MedPro Healthcare",
            "material": "polypropylene",
            "sterility": None,  # Intentionally missing — triggers UNCERTAIN
            "size_label": None,
            "mdr_class": "I",
            "packaging_unit": "Box",
            "units_per_package": 50,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 0.8},
            }),
        },
        {
            "supplier_id": healthguard_id,
            "raw_name": "HealthGuard OP-Maske Typ II mit Bindebändern",
            "article_number": "HG-MASK-II-BIND",
            "brand": "HealthGuard",
            "product_category": "mask",
            "manufacturer": "HealthGuard Medical",
            "material": "polypropylene",
            "sterility": "non-sterile",
            "size_label": None,
            "mdr_class": "I",
            "packaging_unit": "Box",
            "units_per_package": 50,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 1.0},
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Wound Care (HealthGuard) ---
        {
            "supplier_id": healthguard_id,
            "raw_name": "HealthGuard Wundversorgungs-Set steril",
            "article_number": "HG-WC-SET-S",
            "brand": "HealthGuard",
            "product_category": "wound_care",
            "manufacturer": "HealthGuard Medical",
            "sterility": "sterile",
            "size_label": None,
            "mdr_class": None,  # Intentionally missing
            "packaging_unit": "Stück",
            "units_per_package": 1,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Wound Care Dressing Kit sterile",
            "article_number": "MP-WC-KIT-S",
            "brand": "MedPro",
            "product_category": "wound_care",
            "manufacturer": "MedPro Healthcare",
            "sterility": "sterile",
            "size_label": None,
            "mdr_class": "IIa",
            "packaging_unit": "Stück",
            "units_per_package": 1,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
                "mdr_class": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Disinfectant Wipes (MedPro) ---
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Surface Disinfectant Wipes",
            "article_number": "MP-DIS-WIPE",
            "brand": "MedPro CleanSafe",
            "product_category": "disinfectant",
            "manufacturer": "MedPro Healthcare",
            "sterility": None,
            "size_label": None,
            "mdr_class": None,  # Intentionally missing
            "packaging_unit": "Dose",
            "units_per_package": 100,
            "base_unit": "Tuch",
            "provenance_json": json.dumps({}),
        },

        # --- Wound Plaster (HealthGuard) ---
        {
            "supplier_id": healthguard_id,
            "raw_name": "HealthGuard Wundschnellverband elastisch 6 cm × 5 m",
            "article_number": "HG-PL-EL-6x5",
            "brand": "HealthGuard",
            "product_category": "wound_care",
            "product_subcategory": "plaster",
            "manufacturer": "HealthGuard Medical",
            "sterility": None,  # Intentionally missing
            "size_label": "6 cm × 5 m",
            "mdr_class": "I",
            "packaging_unit": "Rolle",
            "units_per_package": 1,
            "base_unit": "Rolle",
            "provenance_json": json.dumps({
                "size_label": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Urine Cup (MedPro) ---
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Urinbecher 100 ml mit Schraubdeckel",
            "article_number": "MP-UR-100",
            "brand": "MedPro",
            "product_category": "urine_collection",
            "manufacturer": "MedPro Healthcare",
            "sterility": None,  # Intentionally missing — triggers UNCERTAIN
            "size_label": "100 ml",
            "dimensions_json": json.dumps({"volume_ml": 100}),
            "mdr_class": "I",
            "packaging_unit": "Stück",
            "units_per_package": 1,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "size_label": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Infusion Set (HealthGuard) ---
        {
            "supplier_id": healthguard_id,
            "raw_name": "HealthGuard Infusionsbesteck mit Sicherheitsventil",
            "article_number": "HG-INF-SAFE",
            "brand": "HealthGuard",
            "product_category": "infusion_set",
            "manufacturer": "HealthGuard Medical",
            "sterility": "sterile",
            "size_label": None,
            "mdr_class": "IIa",
            "packaging_unit": "Stück",
            "units_per_package": 1,
            "base_unit": "Stück",
            "provenance_json": json.dumps({
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
                "mdr_class": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Additional syringe from MedPro (different brand, similar product) ---
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Einmalspritze 10 ml Luer-Lock steril",
            "article_number": "MP-SYR-10LL",
            "brand": "MedPro",
            "product_category": "syringe",
            "product_subcategory": "three_part_luer_lock",
            "manufacturer": "MedPro Healthcare",
            "material": "polypropylene",
            "sterility": "sterile",
            "size_label": "10 ml",
            "dimensions_json": json.dumps({"volume_ml": 10.0}),
            "connector_type": "luer-lock",
            "graduation_ml": 0.5,
            "mdr_class": "IIa",
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7886-1"]),
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 1.0},
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },

        # --- Needle from MedPro (alternative to Sterican) ---
        {
            "supplier_id": medpro_id,
            "raw_name": "MedPro Einmalkanüle 0,80 × 40 mm (21G)",
            "article_number": "MP-NDL-21G-40",
            "brand": "MedPro",
            "product_category": "needle",
            "product_subcategory": "standard_injection",
            "manufacturer": "MedPro Healthcare",
            "material": "stainless_steel",
            "sterility": "sterile",
            "size_label": "0.80 × 40 mm",
            "dimensions_json": json.dumps({"od_mm": 0.80, "length_mm": 40.0, "gauge": "21G"}),
            "connector_type": "luer-lock",
            "mdr_class": None,  # Intentionally missing
            "packaging_unit": "Stück",
            "units_per_package": 100,
            "base_unit": "Stück",
            "din_iso_norms": json.dumps(["DIN EN ISO 7864"]),
            "provenance_json": json.dumps({
                "material": {"source": "supplier_catalog", "confidence": 1.0},
                "sterility": {"source": "supplier_catalog", "confidence": 1.0},
            }),
        },
    ]
