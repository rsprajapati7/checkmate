"""
Seal detection scorer.

Uses YOLOv8 for seal/stamp localization, then analyzes each detected
region with edge sharpness checks for pasted seal detection.
Falls back gracefully when ultralytics/model is not available.
"""

import asyncio
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level YOLO model cache (HIGH-06 fix: loaded once, not per request)
# ---------------------------------------------------------------------------
_YOLO_MODEL_CACHE: Optional[object] = None
_YOLO_MODEL_TRIED: bool = False


@dataclass
class SealResult:
    score: float
    seals_found: int = 0
    suspicious_seals: int = 0
    flags: List[str] = field(default_factory=list)


async def run_seal_pipeline(image_paths: List[str], is_scanned: bool = True) -> SealResult:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_sync, image_paths, is_scanned)


def _run_sync(image_paths: List[str], is_scanned: bool = True) -> SealResult:
    model = _load_yolo_model()
    total_seals = 0
    suspicious = 0
    flags: List[str] = []

    for img_path in image_paths:
        if not os.path.exists(img_path):
            continue
        try:
            seal_regions = _detect_seals(img_path, model, is_scanned=is_scanned)
            total_seals += len(seal_regions)

            # Read the image ONCE per page (MEDIUM-12 fix: was re-reading per seal)
            img_cv = cv2.imread(img_path)
            if img_cv is None:
                continue

            for idx, (x1, y1, x2, y2) in enumerate(seal_regions):
                crop = img_cv[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                lap_var = cv2.Laplacian(gray_crop, cv2.CV_64F).var()
                ela_score = _crop_ela_score(img_path, x1, y1, x2, y2)

                is_suspicious = False
                reason_parts = []

                if is_scanned:
                    # Pasted digital stamps on scanned documents are sharper than
                    # the scanned background and show higher ELA compression mismatch.
                    if lap_var > 500 and ela_score > 1.6:
                        is_suspicious = True
                        reason_parts.append(f"sharpness={lap_var:.0f}")
                        reason_parts.append(f"ELA={ela_score:.2f}")
                    elif ela_score > 4.0:
                        is_suspicious = True
                        reason_parts.append(f"ELA={ela_score:.2f}")
                else:
                    # Digital PDFs: only flag extreme ELA anomalies
                    # (e.g., a low-quality bitmap stamp pasted onto a vector PDF)
                    if ela_score > 6.0:
                        is_suspicious = True
                        reason_parts.append(f"ELA={ela_score:.2f} (bitmap on digital PDF)")

                if is_suspicious:
                    suspicious += 1
                    flags.append(
                        f"Seal #{idx + 1} in {Path(img_path).name} appears pasted "
                        f"({', '.join(reason_parts)})"
                    )

        except Exception as e:
            logger.exception("Seal error on %s: %s", img_path, e)

    if total_seals == 0:
        score = 0.0
    else:
        susp_ratio = suspicious / total_seals
        score = min(100.0, susp_ratio * 80.0 + (suspicious * 5.0))

    logger.info("[Seal] Seals found: %d | Suspicious: %d | Score: %.1f", total_seals, suspicious, score)
    return SealResult(
        score=round(score, 1),
        seals_found=total_seals,
        suspicious_seals=suspicious,
        flags=flags,
    )


def _load_yolo_model():
    """
    Load YOLO model from disk exactly once and cache it for the process lifetime.
    Thread-safe via the GIL — module-level variable access is atomic.
    """
    global _YOLO_MODEL_CACHE, _YOLO_MODEL_TRIED
    if _YOLO_MODEL_TRIED:
        return _YOLO_MODEL_CACHE
    _YOLO_MODEL_TRIED = True
    try:
        from ultralytics import YOLO
        model_path = settings.YOLO_MODEL_PATH
        if os.path.exists(model_path):
            _YOLO_MODEL_CACHE = YOLO(model_path)
            logger.info("[Seal] YOLO model loaded from %s", model_path)
        else:
            logger.warning("[Seal] Custom model not found — using heuristic detection")
    except Exception as e:
        logger.warning("[Seal] YOLO unavailable: %s — using heuristic detection", e)
    return _YOLO_MODEL_CACHE


def _detect_seals(img_path: str, model, is_scanned: bool = True) -> List[tuple]:
    if model is None:
        return _heuristic_seal_detection(img_path, is_scanned=is_scanned)
    try:
        device = "cpu"
        import os
        force_device = os.environ.get("CHECKMATE_DEVICE", "auto").lower()
        if force_device in ("gpu", "cuda"):
            device = "cuda"
        elif force_device == "cpu":
            device = "cpu"
        else:
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
            except ImportError:
                pass
        results = model(img_path, conf=settings.YOLO_CONFIDENCE_THRESHOLD, device=device, verbose=False)
        boxes = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                boxes.append((x1, y1, x2, y2))
        return boxes
    except Exception as e:
        logger.warning("[Seal] YOLO inference failed on device %s: %s", device if 'device' in locals() else 'unknown', e)
        return _heuristic_seal_detection(img_path, is_scanned=is_scanned)


def _heuristic_seal_detection(img_path: str, is_scanned: bool = True) -> List[tuple]:
    img = cv2.imread(img_path)
    if img is None:
        return []

    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Color ranges for typical stamp inks (Red, Blue, Purple)
    lower_red1 = np.array([0, 40, 40])
    upper_red1 = np.array([12, 255, 255])
    lower_red2 = np.array([165, 40, 40])
    upper_red2 = np.array([180, 255, 255])
    lower_blue = np.array([85, 40, 40])
    upper_blue = np.array([130, 255, 255])
    lower_purple = np.array([130, 40, 40])
    upper_purple = np.array([165, 255, 255])

    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_purple = cv2.inRange(hsv, lower_purple, upper_purple)
    combined_mask = mask_red1 | mask_red2 | mask_blue | mask_purple

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    closed = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    min_area = 1500
    max_area = (h * w) * 0.25

    for c in contours:
        area = cv2.contourArea(c)
        if min_area <= area <= max_area:
            x, y, cw, ch = cv2.boundingRect(c)
            pad = 15
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(w, x + cw + pad)
            y2 = min(h, y + ch + pad)
            aspect_ratio = cw / float(ch) if ch > 0 else 0
            if 0.25 <= aspect_ratio <= 4.0:
                boxes.append((x1, y1, x2, y2))

    # NMS/Union merge
    merged_boxes = []
    for box in sorted(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True):
        overlap = False
        for m_box in merged_boxes:
            ix1 = max(box[0], m_box[0])
            iy1 = max(box[1], m_box[1])
            ix2 = min(box[2], m_box[2])
            iy2 = min(box[3], m_box[3])
            if ix2 > ix1 and iy2 > iy1:
                int_area = (ix2 - ix1) * (iy2 - iy1)
                box_area = (box[2] - box[0]) * (box[3] - box[1])
                if int_area / float(box_area) > 0.35:
                    overlap = True
                    break
        if not overlap:
            merged_boxes.append(box)

    # Fallback to Hough Circles if color ink detection yields nothing
    if not merged_boxes:
        logger.info("[Seal Scorer] Color heuristic found no seals. Falling back to Hough Circles.")
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(img_gray, (9, 9), 2)
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=50,
            param1=80, param2=40, minRadius=30, maxRadius=200,
        )
        if circles is not None:
            for (cx, cy, r) in circles[0]:
                x1 = max(0, int(cx - r))
                y1 = max(0, int(cy - r))
                x2 = min(w, int(cx + r))
                y2 = min(h, int(cy + r))
                if (x2 - x1) > 20 and (y2 - y1) > 20:
                    merged_boxes.append((x1, y1, x2, y2))

    return merged_boxes[:5]


def _crop_ela_score(img_path: str, x1: int, y1: int, x2: int, y2: int) -> float:
    try:
        img = Image.open(img_path).convert("RGB")
        orig_np = np.array(img, dtype=np.float32)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)

        recomp = Image.open(buf)
        recomp.load()
        recomp_np = np.array(recomp, dtype=np.float32)

        if orig_np.shape != recomp_np.shape:
            return 0.0

        diff_map = np.abs(orig_np - recomp_np)
        if diff_map.ndim == 3:
            diff_map = np.mean(diff_map, axis=2)

        crop_diff = diff_map[y1:y2, x1:x2]
        if crop_diff.size == 0:
            return 0.0
        return float(np.mean(crop_diff))
    except Exception:
        return 0.0
