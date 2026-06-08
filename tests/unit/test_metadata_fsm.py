"""
Unit tests for metadata forensics anomaly rules.
"""
import pytest
from backend.pipelines.metadata_forensics.anomaly_rules import (
    rule_creation_after_modification,
    rule_missing_metadata,
    rule_future_date,
    rule_incremental_save_anomaly,
    rule_producer_scanner_mismatch,
    rule_xmp_pdf_date_mismatch,
)


class TestMetadataRules:
    def test_creation_before_mod_ok(self):
        meta = {
            "creationDate": "D:20240101120000",
            "modDate": "D:20240601120000",
        }
        triggered, _, _ = rule_creation_after_modification(meta)
        assert not triggered

    def test_creation_after_mod_flags(self):
        meta = {
            "creationDate": "D:20260601120000",
            "modDate": "D:20260101120000",
        }
        triggered, msg, sev = rule_creation_after_modification(meta)
        assert triggered
        assert sev > 0
        assert "CreationDate" in msg

    def test_missing_metadata_two_fields_flags(self):
        meta = {"incremental_save_count": 0}  # no creationDate, creator, producer
        triggered, msg, sev = rule_missing_metadata(meta)
        assert triggered
        assert sev == 0.40

    def test_missing_metadata_one_field_ok(self):
        meta = {"creationDate": "D:20240101", "creator": "Word", "incremental_save_count": 0}
        # Only 'producer' is missing — should NOT trigger (threshold is >= 2)
        triggered, _, _ = rule_missing_metadata(meta)
        assert not triggered

    def test_future_date_flags(self):
        meta = {"creationDate": "D:20990101120000"}
        triggered, msg, sev = rule_future_date(meta)
        assert triggered
        assert sev == 0.90

    def test_normal_date_not_flagged(self):
        meta = {"creationDate": "D:20230601120000"}
        triggered, _, _ = rule_future_date(meta)
        assert not triggered

    def test_incremental_saves_high_flags(self):
        meta = {"incremental_save_count": 10}
        triggered, msg, sev = rule_incremental_save_anomaly(meta)
        assert triggered
        assert "10" in msg

    def test_incremental_saves_low_ok(self):
        meta = {"incremental_save_count": 1}
        triggered, _, _ = rule_incremental_save_anomaly(meta)
        assert not triggered

    def test_scanner_with_photoshop_flags(self):
        meta = {"producer": "HP Scanner 3000", "creator": "Adobe Photoshop CC"}
        triggered, msg, sev = rule_producer_scanner_mismatch(meta)
        assert triggered
        assert sev > 0


class TestMetadataPDFGuard:
    """Verify that image files skip PDF-only metadata rules."""

    def _make_image_ingestion(self):
        """Create a mock IngestionResult for a JPEG image."""
        from dataclasses import dataclass, field
        from typing import List, Optional

        @dataclass
        class MockIngestion:
            file_type: str = "JPG"
            pdf_metadata: Optional[dict] = None
            xmp_metadata: Optional[str] = None
            incremental_save_count: int = 0

        return MockIngestion()

    def test_image_file_scores_zero(self):
        import asyncio
        from backend.pipelines.metadata_forensics.scorer import _run_sync
        from backend.ingestion.engine import IngestionResult, PageData
        from PIL import Image

        # Build a minimal IngestionResult for a JPEG image (no PDF metadata)
        result = IngestionResult(
            document_id="test",
            file_path="Roll.jpeg",
            file_type="JPG",
            file_size_bytes=1000,
            is_scanned=True,
            page_count=1,
            pages=[],
            full_ocr_text="Test OCR text here",
            full_native_text="",
            all_qr_codes=[],
            pdf_metadata=None,
            xmp_metadata=None,
            incremental_save_count=0,
        )
        meta_result = _run_sync(result)
        assert meta_result.score == 0.0, (
            f"Image file should score 0.0 on metadata pipeline, got {meta_result.score}\n"
            f"Flags: {meta_result.flags}"
        )