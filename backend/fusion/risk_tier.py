"""Risk tier classification."""
from backend.core.config import settings
from backend.core.models import RiskTier


def classify_tier(score: float) -> RiskTier:
    """
    Map a fused 0-1 risk score to a risk tier.
    Thresholds are configurable via settings.
    """
    if score < settings.RISK_GREEN_THRESHOLD:
        return RiskTier.GREEN
    elif score < settings.RISK_RED_THRESHOLD:
        return RiskTier.AMBER
    else:
        return RiskTier.RED


def tier_label(tier: RiskTier) -> str:
    labels = {
        RiskTier.GREEN: "Approved",
        RiskTier.AMBER: "Review Queue",
        RiskTier.RED: "AI Investigation Required",
        RiskTier.UNKNOWN: "Unknown",
    }
    return labels.get(tier, "Unknown")
