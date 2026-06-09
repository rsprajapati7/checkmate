"""
ELA Pipeline async adapter — integrates the ELA engine into the CheckMate pipeline.

Fixes the import path issue (analyze.py uses `from ghost import ...` which only
works when run from the ela_forgery/ directory). This adapter uses absolute imports.
"""

import asyncio
import base64
import io
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from PIL import Image

from backend.core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Ensure ela_forgery directory is on sys.path so relative imports inside
# ela.py, ghost.py, analyze.py, docdetect.py, visualize.py work correctly.
# ---------------------------------------------------------------------------
_ELA_DIR = Path(__file__).parent
if str(_ELA_DIR) not in sys.path:
    sys.path.insert(0, str(_ELA_DIR))


@dataclass
class ELAResult:
    score: float                    # 0-100 risk score
    risk_label: str                 # "LOW" | "MODERATE" | "HIGH" | "CRITICAL"
    heatmap_b64: Optional[str]      # base64-encoded PNG heatmap (for report)
    anomalous_regions: int          # number of high-error clusters found
    flags: List[str] = field(default_factory=list)
    per_page_scores: List[float] = field(default_factory=list)


async def run_ela_pipeline(
    image_paths: List[str],
    multiscale: bool = True,
    mask: bool = True,
    is_scanned: bool = True,
) -> ELAResult:
    """
    Run ELA on a list of document page images (PNG paths).
    Returns an ELAResult aggregating all pages.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_ela_sync, image_paths, multiscale, mask, is_scanned)


def _run_ela_sync(image_paths: List[str], multiscale: bool = True, mask: bool = True, is_scanned: bool = True) -> ELAResult:
    """Synchronous ELA execution — runs in a thread pool from the async caller."""
    try:
        # Import from ela_forgery using the patched sys.path
        from ela import compute_ela_multiscale, compute_ela          # noqa: E402
        from docdetect import detect_document_region, generate_text_mask, classify_document_type  # noqa: E402
        from analyze import risk_score, find_anomalous_regions, classify_risk  # noqa: E402
        from visualize import generate_ela_heatmap                  # noqa: E402
    except ImportError as e:
        logger.error(f"[ELA] Import error: {e}")
        return ELAResult(score=0.0, risk_label="LOW", heatmap_b64=None, anomalous_regions=0,
                         flags=["ELA engine unavailable — import error"])

    page_scores: List[float] = []
    all_flags: List[str] = []
    best_heatmap_b64: Optional[str] = None
    best_score = 0.0
    total_regions = 0

    for img_path in image_paths:
        if not os.path.exists(img_path):
            logger.warning(f"[ELA] Image not found: {img_path}")
            continue

        try:
            # Compute ELA error map (multi-scale optional)
            if multiscale:
                error_map = compute_ela_multiscale(img_path)
            else:
                error_map = compute_ela(img_path)

            # Document-aware masks (optional)
            if mask:
                doc_mask = detect_document_region(img_path)
                text_mask = generate_text_mask(img_path, doc_mask)
                doc_type = classify_document_type(img_path, doc_mask)
            else:
                doc_mask = None
                text_mask = None
                doc_type = 'PHOTO'

            # Risk score (0-100)
            score = risk_score(
                error_map,
                block_size=32,
                doc_mask=doc_mask,
                text_mask=text_mask,
                doc_type=doc_type,
                image_path=img_path,
                is_scanned=is_scanned,
            )

            # Anomalous region count
            regions = find_anomalous_regions(error_map, doc_mask=doc_mask)
            total_regions += regions

            page_scores.append(score)

            # Track best (highest) score page for heatmap
            if score > best_score:
                best_score = score
                try:
                    heatmap_arr = generate_ela_heatmap(img_path, error_map, doc_mask=doc_mask)
                    heatmap_img = Image.fromarray(heatmap_arr)
                    buf = io.BytesIO()
                    heatmap_img.save(buf, format="PNG")
                    best_heatmap_b64 = base64.b64encode(buf.getvalue()).decode()
                except Exception as hm_err:
                    logger.warning(f"[ELA] Heatmap generation failed: {hm_err}")

            label, _ = classify_risk(score)
            if score >= 35:
                all_flags.append(f"Page ELA score {score:.1f}/100 ({label})")

            logger.info(f"[ELA] {Path(img_path).name}: score={score:.1f} regions={regions} type={doc_type}")

        except Exception as page_err:
            logger.exception(f"[ELA] Failed on {img_path}: {page_err}")
            page_scores.append(0.0)

    # Aggregate: worst-case (max) page score drives the final result
    final_score = max(page_scores) if page_scores else 0.0
    risk_label, _ = classify_risk(final_score)

    return ELAResult(
        score=final_score,
        risk_label=risk_label,
        heatmap_b64=best_heatmap_b64,
        anomalous_regions=total_regions,
        flags=all_flags,
        per_page_scores=page_scores,
    )
