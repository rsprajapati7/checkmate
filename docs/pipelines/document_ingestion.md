# Pipeline: Document Ingestion

The **Document Ingestion** pipeline is the entry point of the CheckMate Forensic Toolkit. It is responsible for ingestion, parsing, pre-processing, and initial extraction of document assets.

---

## Technical Overview
The ingestion engine takes multi-format documents (PDFs, JPEGs, PNGs) and normalizes them into structured images, text, and embedded metadata:

1. **Format Detection & Page Extraction**:
   * For **PDFs**, the system reads core attributes, page count, and structure. It renders each page into a high-resolution lossless raster image (PNG) at 150-300 DPI.
   * For **Images** (JPEG/PNG/BMP), it loads them directly into memory as PIL/NumPy arrays.
2. **Native Text Extraction**:
   * For digital PDFs, it extracts the native textual layer using layout-aware coordinate readers.
3. **OCR (Optical Character Recognition) Engine**:
   * **GPU-Accelerated EasyOCR**: By default, if an active GPU is detected and CUDA is available, the system passes the rasterized page images to `easyocr` for fast, deep-learning-based English text extraction.
   * **CPU-Bound Tesseract (Fallback)**: If EasyOCR is unavailable or fails, it falls back to standard CPU-bound Tesseract OCR.
   * **Image Preprocessing**: Pre-OCR images undergo Otsu binarization and Gaussian blurring to eliminate background noise, gradients, and low-contrast watermark interference.
4. **Embedded Asset Extraction**:
   * **QR Codes**: Scans rasterized pages for standard QR matrices. Decodes them via `pyzbar` to extract metadata and signatures.
   * **PDF Revision Analysis**: Detects incremental saves, checking how many times a PDF was modified and saved.

---

## Structure of Ingestion Output
The pipeline produces a structured `IngestionResult` object containing:
- **`file_type`**: `PDF` or `IMAGE`.
- **`page_count`**: Total pages found.
- **`full_native_text`**: Text extracted directly from the PDF dictionary.
- **`full_ocr_text`**: Cleaned, filtered OCR text (isolated from border/grid artifacts).
- **`all_qr_codes`**: List of detected QR payloads and coordinates.
- **`incremental_save_count`**: Number of times the PDF was incrementally updated.

---

## Local Inspection
To view details of the ingestion stage on a document:
```powershell
# Run direct analysis and review PDF properties or QR fields in the diagnostic summary
python -m checkmate_cli analyze doc.pdf
```
