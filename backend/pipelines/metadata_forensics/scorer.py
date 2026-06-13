"""
Metadata scorer — combines anomaly rule results into a final 0-100 score.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

from backend.core.logger import get_logger
from backend.ingestion.engine import IngestionResult
from backend.pipelines.metadata_forensics.anomaly_rules import ALL_RULES

logger = get_logger(__name__)


@dataclass
class MetadataResult:
    score: float                    # 0-100
    flags: List[str] = field(default_factory=list)
    raw_metadata: dict = field(default_factory=dict)


async def run_metadata_pipeline(ingestion: IngestionResult) -> MetadataResult:
    """Async entry point — runs in thread pool to avoid blocking."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_sync, ingestion)


def _run_sync(ingestion: IngestionResult) -> MetadataResult:
    is_pdf = ingestion.file_type == "PDF"
    meta = _build_meta_dict(ingestion)
    flags: List[str] = []
    total_severity = 0.0

    # Rules that only make sense for PDF files (metadata dict, dates, incremental saves)
    _PDF_ONLY_RULES = {
        "rule_creation_after_modification",
        "rule_producer_scanner_mismatch",
        "rule_missing_metadata",
        "rule_future_date",
        "rule_incremental_save_anomaly",
        "rule_xmp_pdf_date_mismatch",
        "rule_blank_author_on_official_doc",
    }

    for rule in ALL_RULES:
        if not is_pdf and rule.__name__ in _PDF_ONLY_RULES:
            continue
        try:
            triggered, msg, severity = rule(meta)
            if triggered:
                flags.append(msg)
                total_severity += severity
                logger.info(f"[Metadata] Flag: {msg} (severity={severity})")
        except Exception as e:
            logger.warning(f"[Metadata] Rule error {rule.__name__}: {e}")

    # Normalize to 0-100 — max realistic severity is ~3.5 for a fully forged doc
    score = min(100.0, (total_severity / 3.5) * 100.0)

    logger.info(f"[Metadata] Score: {score:.1f}/100 | Flags: {len(flags)}")
    return MetadataResult(score=round(score, 1), flags=flags, raw_metadata=meta)


def _build_meta_dict(ingestion: IngestionResult) -> dict:
    """Merge PDF metadata + ingestion stats into a flat dict for rule evaluation."""
    meta = {}
    if ingestion.pdf_metadata:
        meta.update(ingestion.pdf_metadata)

    # Normalize common key variants
    for k, v in list(meta.items()):
        meta[k.lower()] = v

    meta["incremental_save_count"] = ingestion.incremental_save_count
    meta["is_scanned"] = ingestion.is_scanned

    # Parse XMP for date fields if available
    if ingestion.xmp_metadata:
        meta["xmp_raw"] = ingestion.xmp_metadata
        # Simple regex extraction for xmp:CreateDate
        import re
        m = re.search(r"xmp:CreateDate[>=]([^<\"]+)", ingestion.xmp_metadata)
        if m:
            meta["xmp_create_date"] = m.group(1).strip()

    return meta
