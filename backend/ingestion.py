# Ingestion Layer
# Handles file upload → conversion pipeline:
#   - PDF files → page images via PyMuPDF (fitz)
#   - Image files → used directly
#   - Text extraction via PyMuPDF / pdfplumber / Tesseract OCR
#   - Metadata extraction via PyPDF2
