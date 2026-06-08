"""Ingestion package — PDF/image parsing, OCR, QR extraction."""
from backend.ingestion.engine import ingest_document, IngestionResult

__all__ = ["ingest_document", "IngestionResult"]
