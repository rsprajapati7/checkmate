"""Pattern detection — fingerprinting and cross-document campaign detection."""
from backend.pattern_detection.campaign_detector import run_pattern_detection, PatternResult

__all__ = ["run_pattern_detection", "PatternResult"]