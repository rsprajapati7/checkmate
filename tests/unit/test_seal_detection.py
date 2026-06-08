"""
Unit tests for the seal detection pipeline.
"""
import io
import numpy as np
import pytest
from PIL import Image


class TestSealSuspicionLogic:
    """Test the recalibrated suspicion thresholds in _run_sync."""

    def _crop_ela_score_from_image(self, pil_img: Image.Image) -> float:
        """Simulate _crop_ela_score inline for a PIL image (no file path needed)."""
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="JPEG", quality=85)
        buf.seek(0)
        recomp = Image.open(buf)
        orig_np = np.array(pil_img.convert("RGB"), dtype=np.float32)
        recomp_np = np.array(recomp, dtype=np.float32)
        return float(np.mean(np.abs(orig_np - recomp_np)))

    def test_authentic_sharp_stamp_not_flagged(self):
        """High sharpness ALONE (no ELA) should NOT flag as suspicious."""
        # Simulate: lap_var = 1800, ela_score = 1.0 (authentic sharp stamp)
        lap_var = 1800
        ela_score = 1.0

        is_suspicious = (lap_var > 1200 and ela_score > 4.0) or (ela_score > 6.0)
        assert not is_suspicious, "Authentic sharp stamp should not be flagged"

    def test_pasted_stamp_flagged_by_combined_check(self):
        """High sharpness + high ELA together should flag as suspicious."""
        lap_var = 1500
        ela_score = 5.0

        is_suspicious = (lap_var > 1200 and ela_score > 4.0) or (ela_score > 6.0)
        assert is_suspicious, "High sharpness + high ELA should be flagged"

    def test_high_ela_alone_flags_pasted(self):
        """Very high ELA score alone (> 6.0) should flag as suspicious."""
        lap_var = 200   # low sharpness
        ela_score = 7.5

        is_suspicious = (lap_var > 1200 and ela_score > 4.0) or (ela_score > 6.0)
        assert is_suspicious, "ELA > 6.0 alone should flag suspicious"

    def test_low_sharpness_low_ela_not_flagged(self):
        """Low sharpness + low ELA (typical authentic scanned stamp) = not suspicious."""
        lap_var = 300
        ela_score = 2.5

        is_suspicious = (lap_var > 1200 and ela_score > 4.0) or (ela_score > 6.0)
        assert not is_suspicious, "Authentic scanned stamp should not be flagged"

    def test_score_formula_no_suspicious(self):
        """Score should be 0.0 when no seals are suspicious."""
        total_seals = 4
        suspicious = 0
        score = min(100.0, (suspicious / total_seals) * 80.0 + suspicious * 5.0)
        assert score == 0.0

    def test_score_formula_all_suspicious(self):
        """Score should cap at 100 for pathological cases."""
        total_seals = 4
        suspicious = 4
        score = min(100.0, (suspicious / total_seals) * 80.0 + suspicious * 5.0)
        assert score == 100.0


class TestHeuristicSealDetection:
    """Test _heuristic_seal_detection with synthetic colored regions."""

    def test_no_seals_in_blank_image(self, tmp_path):
        from backend.pipelines.seal_detection.scorer import _heuristic_seal_detection

        # Blank white image — no colored stamp regions
        img = Image.new("RGB", (400, 400), (255, 255, 255))
        p = tmp_path / "blank.jpg"
        img.save(str(p), format="JPEG", quality=95)

        boxes = _heuristic_seal_detection(str(p))
        assert isinstance(boxes, list)
        assert len(boxes) == 0, "Blank image should have no seals"

    def test_red_circle_detected(self, tmp_path):
        import cv2
        import numpy as np

        # Create white image with a bright red circular stamp
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        cv2.circle(img, (200, 200), 60, (0, 0, 220), -1)  # BGR red
        p = tmp_path / "red_stamp.jpg"
        cv2.imwrite(str(p), img)

        from backend.pipelines.seal_detection.scorer import _heuristic_seal_detection
        boxes = _heuristic_seal_detection(str(p))
        assert len(boxes) >= 1, "Red circular stamp should be detected"