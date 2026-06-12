"""
Anomaly rules for metadata forensic state machine.

Each rule is a function: (metadata_dict) -> (triggered: bool, flag_msg: str, severity: float)
severity is in range [0, 1] — contributes to the final metadata score.
"""

from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

AnomalyRule = Callable[[dict], Tuple[bool, str, float]]


def _parse_date(date_str: str) -> Optional[datetime]:
    """Try to parse common PDF date formats."""
    if not date_str:
        return None
    # PDF date format: D:YYYYMMDDHHmmSS
    if date_str.startswith("D:"):
        date_str = date_str[2:]
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(date_str[:len(fmt)], fmt)
            # Make naive datetimes timezone-aware (assume UTC, as PDF dates are UTC)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def rule_creation_after_modification(meta: dict) -> Tuple[bool, str, float]:
    """Creation date is later than modification date."""
    creation_str = meta.get("creationDate") or meta.get("CreationDate") or ""
    mod_str = meta.get("modDate") or meta.get("ModDate") or ""
    creation = _parse_date(creation_str)
    mod = _parse_date(mod_str)
    if creation and mod and creation > mod:
        return True, f"CreationDate ({creation_str[:14]}) is after ModDate ({mod_str[:14]})", 0.85
    return False, "", 0.0


def rule_producer_scanner_mismatch(meta: dict) -> Tuple[bool, str, float]:
    """PDF producer claims a scanner but also has Photoshop/Illustrator fingerprints."""
    producer = (meta.get("producer") or "").lower()
    creator = (meta.get("creator") or "").lower()
    full = producer + " " + creator
    is_scanner = any(k in full for k in ("scanner", "scan", "ricoh", "xerox", "konica", "fujitsu", "hp officejet"))
    is_edit_tool = any(k in full for k in ("photoshop", "illustrator", "acrobat", "inkscape", "gimp", "word", "libreoffice"))
    if is_scanner and is_edit_tool:
        return True, f"Producer/Creator conflict: scanner + editing tool (Producer='{meta.get('producer')}', Creator='{meta.get('creator')}')", 0.75
    return False, "", 0.0


def rule_missing_metadata(meta: dict) -> Tuple[bool, str, float]:
    """Key fields (CreationDate, Producer, Author) are entirely absent."""
    missing = []
    for key in ("creationDate", "creator", "producer"):
        if not meta.get(key):
            missing.append(key)
    if len(missing) >= 2:
        return True, f"Multiple metadata fields absent: {missing}", 0.40
    return False, "", 0.0


def rule_future_date(meta: dict) -> Tuple[bool, str, float]:
    """Any metadata date is in the future."""
    now = datetime.now(timezone.utc)  # timezone-aware (MEDIUM-17 fix)
    for key in ("creationDate", "modDate"):
        d = _parse_date(meta.get(key) or "")
        if d and d > now:
            return True, f"Metadata date '{key}' is in the future: {meta.get(key)}", 0.90
    return False, "", 0.0


def rule_incremental_save_anomaly(meta: dict) -> Tuple[bool, str, float]:
    """PDF has been incrementally saved many times — repeated editing."""
    saves = meta.get("incremental_save_count") or 0
    if saves > 3:
        return True, f"PDF has {saves} incremental saves (repeated re-editing detected)", 0.55
    return False, "", 0.0


def rule_xmp_pdf_date_mismatch(meta: dict) -> Tuple[bool, str, float]:
    """XMP metadata dates differ significantly from PDF dictionary dates."""
    xmp_create = meta.get("xmp_create_date") or ""
    pdf_create = meta.get("creationDate") or ""
    d_xmp = _parse_date(xmp_create)
    d_pdf = _parse_date(pdf_create)
    if d_xmp and d_pdf:
        delta = abs((d_xmp - d_pdf).total_seconds())
        if delta > 86400:  # more than 1 day apart
            return True, f"XMP creation date differs from PDF dict date by >{int(delta/3600)}h", 0.65
    return False, "", 0.0


def rule_blank_author_on_official_doc(meta: dict) -> Tuple[bool, str, float]:
    """Author field is blank on a digital document."""
    author = (meta.get("author") or "").strip()
    producer = (meta.get("producer") or "").lower()
    if not author and producer:
        return True, "Author field is blank on a digital document", 0.25
    return False, "", 0.0


def rule_design_software_origin(meta: dict) -> Tuple[bool, str, float]:
    """Creator or Producer matches editing/design software (Canva, Photoshop, Figma, etc.)."""
    creator = (meta.get("creator") or "").lower()
    producer = (meta.get("producer") or "").lower()
    full = creator + " " + producer
    # Design/graphic tools that should never generate official certificates/admit cards/bank statements
    design_tools = ("canva", "photoshop", "illustrator", "figma", "sketch", "indesign", "gimp", "inkscape", "coreldraw")
    for tool in design_tools:
        if tool in full:
            return True, f"Document generated or edited with graphic design software: '{tool.capitalize()}' (Creator='{meta.get('creator')}', Producer='{meta.get('producer')}')", 0.80
    return False, "", 0.0


ALL_RULES = [
    rule_creation_after_modification,
    rule_producer_scanner_mismatch,
    rule_missing_metadata,
    rule_future_date,
    rule_incremental_save_anomaly,
    rule_xmp_pdf_date_mismatch,
    rule_blank_author_on_official_doc,
    rule_design_software_origin,
]
