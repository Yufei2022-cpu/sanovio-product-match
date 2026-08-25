"""
Shared normalization utilities for product attributes.

Handles:
- German text normalization for product descriptions
- Unit normalization (Stk → Stück, etc.)
- Dimension parsing from free text (e.g., "0,8 × 40 mm")
- Product category classification from product names
- Sterility extraction from product descriptions
- Connector type extraction
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Unit normalization
# ---------------------------------------------------------------------------

UNIT_MAP = {
    "stk": "Stück",
    "stk.": "Stück",
    "stück": "Stück",
    "stueck": "Stück",
    "st": "Stück",
    "box": "Box",
    "pack": "Pack",
    "packung": "Pack",
    "dose": "Dose",
    "rolle": "Rolle",
    "tuch": "Tuch",
    "tücher": "Tuch",
    "karton": "Karton",
    "beutel": "Beutel",
    "paar": "Paar",
}


def normalize_unit(unit: str) -> str:
    """Normalize German ordering/base unit strings."""
    if not unit:
        return unit
    return UNIT_MAP.get(unit.strip().lower(), unit.strip())


# ---------------------------------------------------------------------------
# GTIN / EAN cleaning
# ---------------------------------------------------------------------------

def clean_gtin(gtin: str) -> Optional[str]:
    """Strip leading apostrophes and whitespace from GTIN/EAN fields."""
    if not gtin:
        return None
    cleaned = gtin.strip().lstrip("'").strip()
    # Remove non-digit characters
    cleaned = re.sub(r"[^0-9]", "", cleaned)
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# Product category classification
# ---------------------------------------------------------------------------

# Keywords → category mapping (ordered by specificity)
CATEGORY_KEYWORDS = [
    # Syringes
    (["einmalspritze", "spritze", "syringe", "injekt", "omnifix", "omnican",
      "perfusor", "exadoral"], "syringe"),
    # Needles / Cannulae
    (["kanüle", "kanülen", "needle", "sterican", "nadel"], "needle"),
    # Pen needles
    (["penkanüle", "pen needle", "omnican fine"], "pen_needle"),
    # Lancets
    (["lanzette", "lancet", "solofix"], "lancet"),
    # Infusion sets
    (["infusionsbesteck", "infusion set", "intrafix"], "infusion_set"),
    # Gloves
    (["handschuh", "handschuhe", "glove", "gloves", "nitril", "latex"], "glove"),
    # Masks
    (["maske", "mask", "op-maske", "mundschutz"], "mask"),
    # Wound care / dressings
    (["verbandstoff", "verband", "wundversorgungs", "wundpflaster",
      "pflaster", "dressing", "bandage", "gauze", "gaze"], "wound_care"),
    # Disinfectants / wipes
    (["desinfektions", "desinfektionstüch", "wipe", "mikrozid",
      "desinfektion"], "disinfectant"),
    # Urine collection
    (["urinbecher", "urin", "urine"], "urine_collection"),
    # Sharps containers
    (["medibox", "abfallbehält", "sharps container"], "sharps_container"),
    # Filter needles
    (["filterkanüle", "filter needle", "sterifix"], "filter_needle"),
]


def classify_product_category(name: str) -> Optional[str]:
    """Classify a product into a category based on its name."""
    if not name:
        return None
    name_lower = name.lower()
    for keywords, category in CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in name_lower:
                return category
    return None


# ---------------------------------------------------------------------------
# Sterility extraction
# ---------------------------------------------------------------------------

STERILE_PATTERNS = [
    r"\bsteril\b",
    r"\bsterile\b",
    r"\bsterilisiert\b",
    r"\bsteril verpackt\b",
    r"\beinzeln steril\b",
]

NON_STERILE_PATTERNS = [
    r"\bnicht[- ]?steril\b",
    r"\bnon[- ]?steril\b",
    r"\bunsteril\b",
    r"\bnon[- ]?sterile\b",
]


def extract_sterility(text: str) -> Optional[str]:
    """Extract sterility from product description text."""
    if not text:
        return None
    text_lower = text.lower()

    # Check non-sterile first (more specific)
    for pattern in NON_STERILE_PATTERNS:
        if re.search(pattern, text_lower):
            return "non-sterile"

    # Then check sterile
    for pattern in STERILE_PATTERNS:
        if re.search(pattern, text_lower):
            return "sterile"

    return None


# ---------------------------------------------------------------------------
# Connector type extraction
# ---------------------------------------------------------------------------

def extract_connector_type(text: str) -> Optional[str]:
    """Extract syringe/needle connector type from product text."""
    if not text:
        return None
    text_lower = text.lower()

    if "nrfit" in text_lower or "nr-fit" in text_lower:
        return "nrfit"
    if "luer-lock" in text_lower or "luer lock" in text_lower:
        return "luer-lock"
    if "katheteransatz" in text_lower or "katheter" in text_lower:
        return "catheter"
    if "oral" in text_lower and "ansatz" in text_lower:
        return "oral"
    if "luer" in text_lower:
        return "luer"

    return None


# ---------------------------------------------------------------------------
# Material extraction
# ---------------------------------------------------------------------------

MATERIAL_KEYWORDS = {
    "nitril": "nitrile",
    "nitrile": "nitrile",
    "latex": "latex",
    "vinyl": "vinyl",
    "polypropylen": "polypropylene",
    "polypropylene": "polypropylene",
    "polyethylen": "polyethylene",
    "polyethylene": "polyethylene",
    "polyisopren": "polyisoprene",
    "polystyrol": "polystyrene",
    "chrom-nickel-stahl": "stainless_steel",
    "edelstahl": "stainless_steel",
    "stainless steel": "stainless_steel",
}


def extract_material(text: str) -> Optional[str]:
    """Extract material from product description."""
    if not text:
        return None
    text_lower = text.lower()
    for keyword, material in MATERIAL_KEYWORDS.items():
        if keyword in text_lower:
            return material
    return None


# ---------------------------------------------------------------------------
# Dimension / Size parsing
# ---------------------------------------------------------------------------

def parse_syringe_size(text: str) -> Optional[dict]:
    """Extract syringe volume from text like '10 ml' or '10ml'."""
    if not text:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*ml", text.lower())
    if match:
        vol = float(match.group(1).replace(",", "."))
        return {"volume_ml": vol}
    return None


def parse_needle_dimensions(text: str) -> Optional[dict]:
    """Extract needle dimensions from text like '0,8 × 40 mm' or '0.8 x 40 mm'."""
    if not text:
        return None
    # Match patterns like "0,8 × 40 mm" or "0.80 x 40 mm"
    match = re.search(
        r"(\d+[.,]\d+)\s*[×xX]\s*(\d+(?:[.,]\d+)?)\s*mm",
        text
    )
    if match:
        od = float(match.group(1).replace(",", "."))
        length = float(match.group(2).replace(",", "."))
        return {"od_mm": od, "length_mm": length}
    return None


def parse_gauge(text: str) -> Optional[str]:
    """Extract gauge from text like '21 G' or '21G'."""
    if not text:
        return None
    match = re.search(r"(\d+)\s*G\b", text)
    if match:
        return f"{match.group(1)}G"
    return None


def extract_size_label(name: str, category: Optional[str] = None) -> Optional[str]:
    """Extract a human-readable size label from a product name."""
    if not name:
        return None

    # Syringe: look for ml
    ml_match = re.search(r"(\d+(?:[.,]\d+)?)\s*ml", name.lower())
    if ml_match:
        vol = ml_match.group(1).replace(",", ".")
        return f"{vol} ml"

    # Needle: look for dimensions
    dim_match = re.search(r"(\d+[.,]\d+\s*[×xX]\s*\d+(?:[.,]\d+)?)\s*mm", name)
    if dim_match:
        return f"{dim_match.group(1)} mm"

    # Gloves/general: look for size letters
    size_match = re.search(r"\b(XXS|XS|S|M|L|XL|XXL)\b", name, re.IGNORECASE)
    if size_match:
        return size_match.group(1).upper()

    # Plaster/wound care: look for cm dimensions
    cm_match = re.search(r"(\d+(?:[.,]\d+)?\s*cm\s*[×xX]\s*\d+(?:[.,]\d+)?\s*(?:cm|m))", name)
    if cm_match:
        return cm_match.group(1)

    # Volume for containers
    vol_match = re.search(r"(\d+)\s*ml", name.lower())
    if vol_match:
        return f"{vol_match.group(1)} ml"

    return None


def parse_dimensions(name: str, category: Optional[str] = None) -> Optional[dict]:
    """Parse dimensions from product name based on category."""
    if not name:
        return None

    if category == "syringe":
        return parse_syringe_size(name)
    elif category in ("needle", "pen_needle", "filter_needle"):
        return parse_needle_dimensions(name)
    else:
        # Try syringe first, then needle
        result = parse_syringe_size(name)
        if result:
            return result
        return parse_needle_dimensions(name)


# ---------------------------------------------------------------------------
# Packaging parsing
# ---------------------------------------------------------------------------

def parse_packaging(text: str) -> tuple[Optional[str], Optional[int]]:
    """
    Parse packaging info like '20 x 100 Stück' or '100 Stück'.
    Returns (packaging_unit, units_per_package).
    """
    if not text:
        return None, None

    # Pattern: "N x M Stück" (carton format)
    match = re.search(r"(\d+)\s*[xX×]\s*(\d+)\s*(\w+)", text)
    if match:
        units = int(match.group(2))
        unit = normalize_unit(match.group(3))
        return unit, units

    # Pattern: "N Stück"
    match = re.search(r"(\d+)\s*(\w+)", text)
    if match:
        units = int(match.group(1))
        unit = normalize_unit(match.group(2))
        return unit, units

    return None, None


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    # Normalize common German special chars
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss")
    return text


def tokenize(text: str) -> set[str]:
    """Tokenize text into a set of normalized words."""
    normalized = normalize_text(text)
    # Split on non-alphanumeric characters
    tokens = re.split(r"[^a-z0-9äöüß]+", normalized)
    return {t for t in tokens if len(t) > 1}
