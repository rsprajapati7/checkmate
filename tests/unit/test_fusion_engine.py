"""
Unit tests for the fusion engine.
"""
import pytest
from backend.fusion.engine import fuse_scores
from backend.core.models import RiskTier


class TestFusionEngine:
    def test_all_zero_scores_green(self):
        result = fuse_scores(0.0, 0.0, 0.0, 0.0)
        assert result.final_score == 0.0
        assert result.risk_tier == RiskTier.GREEN

    def test_high_ela_drives_red(self):
        """A very high ELA score (weight 0.35) should push into RED tier."""
        result = fuse_scores(ela_score=100.0, metadata_score=0.0,
                             seal_score=0.0, nlp_score=0.0)
        # ELA contributes 0.35 to final_score → above 0.30 threshold
        assert result.final_score >= 0.30
        assert result.risk_tier in (RiskTier.AMBER, RiskTier.RED)

    def test_all_max_scores_red(self):
        result = fuse_scores(100.0, 100.0, 100.0, 100.0)
        assert result.final_score == 1.0
        assert result.risk_tier == RiskTier.RED

    def test_moderate_scores_amber(self):
        """Combined moderate scores should land in AMBER."""
        result = fuse_scores(40.0, 40.0, 40.0, 40.0)
        # final ≈ 0.40 * (0.35 + 0.25 + 0.25 + 0.15) = 0.40
        assert 0.30 <= result.final_score <= 0.60
        assert result.risk_tier == RiskTier.AMBER

    def test_weights_sum_correct(self):
        """Weights must sum to 1.0 — verify via equal-input test."""
        # With all inputs = 100, output should be 1.0
        result = fuse_scores(100.0, 100.0, 100.0, 100.0)
        assert result.final_score == 1.0

    def test_final_score_clamped_to_one(self):
        """Score should never exceed 1.0."""
        result = fuse_scores(200.0, 200.0, 200.0, 200.0)
        assert result.final_score <= 1.0

    def test_final_score_clamped_to_zero(self):
        """Score should never go below 0.0."""
        result = fuse_scores(-10.0, -10.0, -10.0, -10.0)
        assert result.final_score >= 0.0

    def test_result_has_all_fields(self):
        result = fuse_scores(50.0, 20.0, 30.0, 10.0)
        assert hasattr(result, "ela_score")
        assert hasattr(result, "metadata_score")
        assert hasattr(result, "seal_score")
        assert hasattr(result, "nlp_score")
        assert hasattr(result, "final_score")
        assert hasattr(result, "risk_tier")
        assert hasattr(result, "tier_label")
        assert isinstance(result.tier_label, str)
        assert len(result.tier_label) > 0

    def test_seal_score_contributes_correctly(self):
        """Seal score has weight 0.25; verifying contribution."""
        r_no_seal = fuse_scores(0.0, 0.0, 0.0, 0.0)
        r_max_seal = fuse_scores(0.0, 0.0, 100.0, 0.0)
        diff = r_max_seal.final_score - r_no_seal.final_score
        assert abs(diff - 0.25) < 0.001, f"Seal weight mismatch: diff={diff}"