"""
OCR utilities — ported from ingestion_test (1).py.

Provides:
  - preprocess_image_for_ocr(): Otsu binarization for Tesseract
  - clean_extracted_text(): filter border/artifact lines from OCR output
  - run_tesseract(): full OCR on a PIL image
"""

import re

import cv2
import numpy as np
import pytesseract
from PIL import Image

from backend.core.config import settings

# Point Tesseract to the configured binary path
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def preprocess_image_for_ocr(pil_img: Image.Image) -> Image.Image:
    """
    Applies Otsu binarization to remove background watermarks and gradients
    while preserving character stroke integrity.
    """
    open_cv_image = np.array(pil_img)

    # Handle color channel alignment
    if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 3:
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    # Gaussian blur to reduce salt-and-pepper noise before thresholding
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Otsu's global thresholding — auto-calculates threshold from bimodal histogram
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return Image.fromarray(thresh)


def clean_extracted_text(raw_text: str) -> str:
    """
    Filters OCR output line-by-line:
    - Removes lines dominated by non-alphanumeric chars (border/graphic artifacts)
    - Removes isolated stray punctuation particles
    - Collapses wide blank gaps to a clean double-newline format
    """
    cleaned_lines = []
    for line in raw_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        alnum_chars = sum(1 for ch in stripped if ch.isalnum())
        total_chars = len(stripped)

        # Skip lines that are mostly non-alphanumeric (graphical border artifacts)
        if total_chars > 0 and (alnum_chars / total_chars) < 0.35:
            continue

        # Skip stray isolated punctuation particles
        if len(stripped) <= 2 and not stripped.isalnum():
            continue

        cleaned_lines.append(line)

    final = "\n".join(cleaned_lines)
    final = re.sub(r'\n{3,}', '\n\n', final)
    return final.strip()


def run_tesseract(pil_img: Image.Image, lang: str = "eng") -> str:
    """
    Full OCR pipeline: preprocess → Tesseract → clean text.
    Returns cleaned text string.
    """
    cleaned_img = preprocess_image_for_ocr(pil_img)
    raw = pytesseract.image_to_string(cleaned_img, lang=lang)
    return clean_extracted_text(raw)
