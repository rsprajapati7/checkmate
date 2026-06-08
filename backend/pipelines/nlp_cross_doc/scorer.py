"""
NLP cross-document pipeline scorer.

Aggregates entity extraction + accounting rules into a 0-100 score.
Also performs QR code key-value cross-verification against OCR text.
"""

import ast
import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List

from backend.core.logger import get_logger
from backend.ingestion.engine import IngestionResult
from backend.pipelines.nlp_cross_doc.entity_extractor import ExtractedEntities, extract_entities
from backend.pipelines.nlp_cross_doc.accounting_rules import (
    check_pan_consistency,
    check_aadhaar_consistency,
    check_gst_consistency,
    check_revenue_gst_consistency,
    check_balance_sheet,
)

logger = get_logger(__name__)


@dataclass
class NLPResult:
    score: float
    flags: List[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)    # serializable entity summary


# ---------------------------------------------------------------------------
# QR data parser
# ---------------------------------------------------------------------------

def parse_qr_data(data: str) -> Dict[str, str]:
    """
    Safely parse a QR code data string into a key-value dict.

    Handles:
    - JSON objects: {"key": "value", ...}
    - Python dict literals: {'key': 'value', ...}  (common in pyzbar output)
    - Query-string / key=value pairs: key1=value1&key2=value2
    """
    data = data.strip()

    # Try JSON first
    try:
        parsed = json.loads(data)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except (json.JSONDecodeError, ValueError):
        pass

    # Try Python dict literal (pyzbar often returns repr-style dicts)
    try:
        parsed = ast.literal_eval(data)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except (ValueError, SyntaxError):
        pass

    # Try key=value pairs (URL-style or comma/semicolon-separated)
    result: Dict[str, str] = {}
    for pair in re.split(r'[&;,\n]', data):
        if '=' in pair:
            k, _, v = pair.partition('=')
            k, v = k.strip().strip("'\""), v.strip().strip("'\"")
            if k:
                result[k] = v
    return result


# ---------------------------------------------------------------------------
# QR vs OCR cross-checker
# ---------------------------------------------------------------------------

def _cross_check_qr_fields(
    qr_dict: Dict[str, str],
    ocr_text: str,
    flags: List[str],
) -> float:
    """
    Check that key values from a QR code payload appear in the OCR text.

    Returns additional severity score (0.0–1.0).
    """
    # Fields to skip in cross-check (numeric codes, empty values, etc.)
    SKIP_KEYS = {"sub1", "sub2", "sub3", "sub4", "sub5", "sub6", "sub7",
                 "rollno", "schoolno", "centerno", "medium"}

    ocr_lower = ocr_text.lower()
    mismatches: List[str] = []

    for key, value in qr_dict.items():
        key_norm = key.lower().replace(" ", "").replace("_", "")
        if key_norm in SKIP_KEYS:
            continue
        if not value or value.strip() in ("", "0", "None"):
            continue
        if value.lower() not in ocr_lower:
            mismatches.append(f"{key}='{value}'")

    if mismatches:
        flags.append(
            f"QR payload fields not found in OCR text: {', '.join(mismatches)}"
        )
        # Severity proportional to mismatch count, capped at 0.90
        return min(0.90, len(mismatches) * 0.20)

    return 0.0


# ---------------------------------------------------------------------------
# Async entry point
# ---------------------------------------------------------------------------

async def run_nlp_pipeline(ingestion: IngestionResult) -> NLPResult:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_sync, ingestion)


def _run_sync(ingestion: IngestionResult) -> NLPResult:
    # Use OCR text as the primary source; fall back to native text if OCR is sparse
    text = ingestion.full_ocr_text
    if len(text.strip()) < 100 and ingestion.full_native_text:
        text = ingestion.full_native_text

    entities = extract_entities(text)

    flags: List[str] = []
    total_severity = 0.0

    # --- ID consistency checks ---
    if len(entities.pan_numbers) > 0:
        triggered, msg = check_pan_consistency(entities.pan_numbers)
        if triggered:
            flags.append(msg)
            total_severity += 0.70

    if len(entities.aadhaar_numbers) > 0:
        triggered, msg = check_aadhaar_consistency(entities.aadhaar_numbers)
        if triggered:
            flags.append(msg)
            total_severity += 0.70

    if len(entities.gst_numbers) > 0:
        triggered, msg = check_gst_consistency(entities.gst_numbers)
        if triggered:
            flags.append(msg)
            total_severity += 0.55

    # --- Financial consistency checks (if enough amounts extracted) ---
    amounts = sorted(entities.money_amounts, reverse=True)
    if len(amounts) >= 3:
        assets, liabilities, equity = amounts[0], amounts[1], amounts[2]
        triggered, msg = check_balance_sheet(assets, liabilities, equity)
        if triggered:
            flags.append(msg)
            total_severity += 0.50

    if len(amounts) >= 2:
        revenue, gst_turnover = amounts[0], amounts[1]
        triggered, msg = check_revenue_gst_consistency(revenue, gst_turnover)
        if triggered:
            flags.append(msg)
            total_severity += 0.40

    # --- QR vs OCR cross-check ---
    if ingestion.all_qr_codes:
        for qr in ingestion.all_qr_codes:
            qr_dict = parse_qr_data(qr.data)

            if qr_dict:
                # Cross-check structured QR fields against OCR text
                sev = _cross_check_qr_fields(qr_dict, text, flags)
                total_severity += sev

                # Also extract entities from QR values for PAN/Aadhaar comparison
                qr_text = " ".join(qr_dict.values())
                qr_entities = extract_entities(qr_text)

                ocr_pans = set(entities.pan_numbers)
                qr_pans = set(qr_entities.pan_numbers)
                if ocr_pans and qr_pans and not ocr_pans.intersection(qr_pans):
                    flags.append(
                        f"PAN in QR ({qr_pans}) does not match OCR text ({ocr_pans})"
                    )
                    total_severity += 0.80

                ocr_aadhaar = set(entities.aadhaar_numbers)
                qr_aadhaar = set(qr_entities.aadhaar_numbers)
                if ocr_aadhaar and qr_aadhaar and not ocr_aadhaar.intersection(qr_aadhaar):
                    flags.append(
                        f"Aadhaar in QR ({qr_aadhaar}) does not match OCR text ({ocr_aadhaar})"
                    )
                    total_severity += 0.80

            else:
                # Fallback: raw text comparison (old behaviour for non-structured QR)
                qr_raw_text = qr.data
                qr_entities = extract_entities(qr_raw_text)
                ocr_pans = set(entities.pan_numbers)
                qr_pans = set(qr_entities.pan_numbers)
                if ocr_pans and qr_pans and not ocr_pans.intersection(qr_pans):
                    flags.append(
                        f"PAN in QR code ({qr_pans}) does not match OCR text ({ocr_pans})"
                    )
                    total_severity += 0.80

    # Normalize score: max realistic severity for a single doc is ~2.5
    score = min(100.0, (total_severity / 2.5) * 100.0)

    entity_summary = {
        "pan_numbers": entities.pan_numbers,
        "aadhaar_numbers": entities.aadhaar_numbers,
        "gst_numbers": entities.gst_numbers,
        "money_amounts": entities.money_amounts[:10],
        "person_names": entities.person_names[:10],
    }

    logger.info(
        f"[NLP] Score: {score:.1f}/100 | PANs: {entities.pan_numbers} "
        f"| Flags: {len(flags)}"
    )
    return NLPResult(score=round(score, 1), flags=flags, entities=entity_summary)
