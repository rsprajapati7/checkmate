"""
Unit tests for the ELA forgery pipeline.
"""
import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

# Ensure ela_forgery is importable
_ELA_DIR = Path(__file__).parent.parent.parent / "backend" / "pipelines" / "ela_forgery"
if str(_ELA_DIR) not in sys.path:
    sys.path.insert(0, str(_ELA_DIR))


class TestELACore:
    def _make_jpeg(self, size=(100, 100), quality=95):
        """Create a synthetic JPEG image in a temp BytesIO, return path via tmp_path fixture."""
        img = Image.new("RGB", size, color=(180, 180, 180))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf

    def test_compute_ela_returns_2d_float32(self, tmp_path):
        from ela import compute_ela

        # Create a clean JPEG
        img = Image.new("RGB", (100, 100), (200, 200, 200))
        p = tmp_path / "test.jpg"
        img.save(str(p), format="JPEG", quality=95)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            emap = compute_ela(str(p), quality=85)

        assert emap.ndim == 2, "ELA map should be 2D"
        assert emap.dtype == np.float32
        assert emap.shape == (100, 100)

    def test_clean_image_low_ela_score(self, tmp_path):
        """A uniform clean image should produce a low ELA score."""
        from ela import compute_ela_multiscale
        from analyze import risk_score

        img = Image.new("RGB", (200, 200), (150, 150, 150))
        p = tmp_path / "clean.jpg"
        img.save(str(p), format="JPEG", quality=95)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            emap = compute_ela_multiscale(str(p))
            score = risk_score(emap, block_size=32, image_path=str(p))

        assert score < 50.0, f"Clean image should score below 50, got {score}"

    def test_non_jpeg_warns(self, tmp_path):
        """A PNG input should trigger a UserWarning."""
        from ela import compute_ela

        img = Image.new("RGB", (100, 100), (100, 100, 100))
        p = tmp_path / "test.png"
        img.save(str(p), format="PNG")

        with pytest.warns(UserWarning, match="not JPEG"):
            compute_ela(str(p))


class TestELAMultiscale:
    def test_multiscale_returns_scaled_map(self, tmp_path):
        from ela import compute_ela_multiscale

        img = Image.new("RGB", (150, 150), (128, 128, 128))
        p = tmp_path / "multi.jpg"
        img.save(str(p), format="JPEG", quality=90)

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            emap = compute_ela_multiscale(str(p), qualities=(75, 85, 95))

        assert emap.ndim == 2
        assert emap.max() <= 255.0
        assert emap.min() >= 0.0