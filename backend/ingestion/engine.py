"""
Ingestion engine — main entry point for document parsing.

Handles:
  - PDF → per-page JPEG conversion (300 DPI via PyMuPDF)
  - Direct image (PNG/JPG) loading
  - OCR via Tesseract (with Otsu binarization)
  - QR code extraction (pyzbar)
  - File system + PDF metadata extraction
  - is_scanned detection via majority-rule across all pages

Returns an IngestionResult dataclass consumed by all downstream pipelines.
"""

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pymupdf  # PyMuPDF
from PIL import Image

from backend.core.exceptions import IngestionError
from backend.core.logger import get_logger
from backend.ingestion.ocr import run_tesseract
from backend.ingestion.qr_extractor import QRResult, extract_qr_from_pages

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


@dataclass
class PageData:
    page_num: int           # 1-indexed
    image_path: str         # saved JPEG path for ELA + seal detection
    ocr_text: str           # Tesseract OCR output
    native_text: str        # Embedded PDF text layer (empty for scanned/images)
    qr_codes: List[QRResult] = field(default_factory=list)
    # NOTE: pil_image removed — it was held in RAM for the entire pipeline duration
    # (up to 30 MB per page uncompressed). All downstream pipelines use image_path instead.


@dataclass
class IngestionResult:
    document_id: str
    file_path: str
    file_type: str              # "PDF" | "PNG" | "JPG"
    file_size_bytes: int
    is_scanned: bool
    page_count: int
    pages: List[PageData]

    # Aggregated text across all pages
    full_ocr_text: str
    full_native_text: str

    # All QR codes found across all pages
    all_qr_codes: List[QRResult]

    # PDF metadata (None for images)
    pdf_metadata: Optional[dict] = None
    xmp_metadata: Optional[str] = None
    incremental_save_count: int = 0


def ingest_document(file_path: str, document_id: str, output_dir: str) -> IngestionResult:
    """
    Parse a PDF or image file into a structured IngestionResult.

    Parameters
    ----------
    file_path : str
        Absolute path to the uploaded file.
    document_id : str
        Job/document UUID for naming output files.
    output_dir : str
        Directory to write per-page JPEG renders (used downstream by ELA).

    Returns
    -------
    IngestionResult
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise IngestionError(f"Unsupported file type: {ext}")

    file_bytes = path.read_bytes()
    os.makedirs(output_dir, exist_ok=True)

    logger.info("[Ingestion] Starting: %s (%d bytes)", path.name, len(file_bytes))

    if ext == ".pdf":
        return _ingest_pdf(file_path, file_bytes, document_id, output_dir)
    else:
        return _ingest_image(file_path, file_bytes, ext, document_id, output_dir)


# ---------------------------------------------------------------------------
# PDF ingestion
# ---------------------------------------------------------------------------

def _ingest_pdf(
    file_path: str,
    file_bytes: bytes,
    document_id: str,
    output_dir: str,
) -> IngestionResult:
    try:
        doc = pymupdf.open(file_path)
    except Exception as e:
        raise IngestionError(f"PyMuPDF could not open PDF: {e}") from e

    # --- is_scanned: majority-rule across ALL pages (HIGH-15 fix) ---
    # Previously only checked the first page, which caused multi-page PDFs with
    # a scanned cover to be misclassified as fully scanned.
    pages_with_native_text = sum(
        1 for page in doc if page.get_text().strip()
    )
    is_scanned = (pages_with_native_text / max(1, len(doc))) < 0.5

    pages: List[PageData] = []
    all_qr: List[QRResult] = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Render at 300 DPI for high-quality ELA + seal detection
        pix = page.get_pixmap(dpi=300)

        img_filename = f"{document_id}_page_{page_num + 1}.jpg"
        img_path = os.path.join(output_dir, img_filename)

        # --- Efficient pixel decode (MEDIUM-11 fix: previously decoded twice via PNG) ---
        # Use raw pixmap samples directly — no intermediate PNG encode/decode cycle.
        pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pil_img.save(img_path, format="JPEG", quality=95)

        # OCR on a 50%-scaled copy — 4× fewer pixels → 3-4× faster on Tesseract/EasyOCR.
        # ELA and seal detection continue to use the full-resolution JPEG on disk.
        ocr_img = pil_img.resize(
            (pix.width // 2, pix.height // 2), Image.LANCZOS
        )
        ocr_text = run_tesseract(ocr_img)
        del ocr_img

        # Native text layer
        native_text = page.get_text().strip() if not is_scanned else ""

        # QR codes
        qr_codes = []
        try:
            from backend.ingestion.qr_extractor import extract_qr_codes
            qr_codes = extract_qr_codes(pil_img)
            all_qr.extend(qr_codes)
        except Exception as qr_err:
            logger.warning("QR extraction failed on page %d: %s", page_num + 1, qr_err)

        # PIL image is no longer stored in PageData — drop reference immediately
        del pil_img

        pages.append(PageData(
            page_num=page_num + 1,
            image_path=img_path,
            ocr_text=ocr_text,
            native_text=native_text,
            qr_codes=qr_codes,
        ))

        logger.info(
            "[Ingestion] Page %d/%d done | OCR chars: %d",
            page_num + 1, len(doc), len(ocr_text),
        )

    # PDF metadata
    pdf_meta = dict(doc.metadata) if doc.metadata else {}
    xmp = None
    try:
        xmp = doc.get_xml_metadata()
    except Exception:
        xmp = None

    incremental_saves = file_bytes.count(b"%%EOF")

    doc.close()

    full_ocr = "\n\n".join(p.ocr_text for p in pages)
    full_native = "\n\n".join(p.native_text for p in pages)

    return IngestionResult(
        document_id=document_id,
        file_path=file_path,
        file_type="PDF",
        file_size_bytes=len(file_bytes),
        is_scanned=is_scanned,
        page_count=len(pages),
        pages=pages,
        full_ocr_text=full_ocr,
        full_native_text=full_native,
        all_qr_codes=all_qr,
        pdf_metadata=pdf_meta,
        xmp_metadata=xmp,
        incremental_save_count=incremental_saves,
    )


# ---------------------------------------------------------------------------
# Image ingestion (PNG / JPG)
# ---------------------------------------------------------------------------

def _ingest_image(
    file_path: str,
    file_bytes: bytes,
    ext: str,
    document_id: str,
    output_dir: str,
) -> IngestionResult:
    try:
        pil_img = Image.open(file_path)
    except Exception as e:
        raise IngestionError(f"Pillow could not open image: {e}") from e

    # Save a copy to output_dir for ELA + seal detection
    img_filename = f"{document_id}_page_1{ext}"
    img_path = os.path.join(output_dir, img_filename)
    with open(img_path, "wb") as f:
        f.write(file_bytes)

    # OCR
    ocr_text = run_tesseract(pil_img)

    # QR
    qr_codes = []
    try:
        from backend.ingestion.qr_extractor import extract_qr_codes
        qr_codes = extract_qr_codes(pil_img)
    except Exception:
        pass

    # PIL image no longer needed — drop reference
    del pil_img

    file_type = ext.replace(".", "").upper()
    if file_type == "JPEG":
        file_type = "JPG"

    page = PageData(
        page_num=1,
        image_path=img_path,
        ocr_text=ocr_text,
        native_text="",
        qr_codes=qr_codes,
    )

    return IngestionResult(
        document_id=document_id,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        is_scanned=True,
        page_count=1,
        pages=[page],
        full_ocr_text=ocr_text,
        full_native_text="",
        all_qr_codes=qr_codes,
        pdf_metadata=None,
        xmp_metadata=None,
        incremental_save_count=0,
    )
