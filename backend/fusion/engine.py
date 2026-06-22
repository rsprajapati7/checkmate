"""
Weighted Bayesian fusion engine.

Combines scores from all 4 forensic pipelines into a final 0-1 risk score.

Scanned document weights (configurable via .env):
  ELA (pixel tampering):    WEIGHT_ELA       (default 0.35)
  Metadata forensics:       WEIGHT_METADATA   (default 0.25)
  Seal analysis:            WEIGHT_SEAL       (default 0.25)
  NLP cross-document:       WEIGHT_NLP        (default 0.15)

Digital (native PDF) document weights (configurable via .env):
  ELA:      WEIGHT_ELA_DIGITAL      (default 0.20)
  Metadata: WEIGHT_METADATA_DIGITAL (default 0.45)
  Seal:     WEIGHT_SEAL_DIGITAL     (default 0.15)
  NLP:      WEIGHT_NLP_DIGITAL      (default 0.20)
"""

from dataclasses import dataclass

from backend.core.config import settings
from backend.core.models import RiskTier
from backend.fusion.risk_tier import classify_tier, tier_label
from backend.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FusionResult:
    # Raw pipeline scores (0-100)
    ela_score: float
    metadata_score: float
    seal_score: float
    nlp_score: float

    # Normalized weighted score (0-1)
    final_score: float

    # Risk classification
    risk_tier: RiskTier
    tier_label: str


def fuse_scores(
    ela_score: float,
    metadata_score: float,
    seal_score: float,
    nlp_score: float,
    is_scanned: bool = True,
) -> FusionResult:
    """
    Compute weighted average of pipeline scores and classify into risk tier.

    All input scores are 0-100. Output final_score is 0-1.

    When is_scanned=False (native digital PDF), a document-type-aware weight
    profile is applied that downweights ELA and Seal (which have higher
    false-positive rates on digital documents) and upweights Metadata
    (which remains fully reliable regardless of document type).

    Both weight profiles are fully configurable via environment variables
    (see Settings in config.py). They are validated to sum to 1.0 at startup.
    """
    # Normalize to 0-1
    ela_n = ela_score / 100.0
    meta_n = metadata_score / 100.0
    seal_n = seal_score / 100.0
    nlp_n = nlp_score / 100.0

    if is_scanned:
        w_ela = settings.WEIGHT_ELA
        w_meta = settings.WEIGHT_METADATA
        w_seal = settings.WEIGHT_SEAL
        w_nlp = settings.WEIGHT_NLP
    else:
        # Digital document weights — sourced from settings, not hardcoded (HIGH-14 fix)
        w_ela = settings.WEIGHT_ELA_DIGITAL
        w_meta = settings.WEIGHT_METADATA_DIGITAL
        w_seal = settings.WEIGHT_SEAL_DIGITAL
        w_nlp = settings.WEIGHT_NLP_DIGITAL

    # Weighted fusion
    final = (
        w_ela * ela_n +
        w_meta * meta_n +
        w_seal * seal_n +
        w_nlp * nlp_n
    )
    final = round(min(1.0, max(0.0, final)), 4)

    tier = classify_tier(final)
    label = tier_label(tier)

    logger.info(
        "[Fusion] ELA=%.1f Meta=%.1f Seal=%.1f NLP=%.1f is_scanned=%s -> Final=%.3f (%s)",
        ela_score, metadata_score, seal_score, nlp_score, is_scanned, final, tier.value,
    )

    return FusionResult(
        ela_score=ela_score,
        metadata_score=metadata_score,
        seal_score=seal_score,
        nlp_score=nlp_score,
        final_score=final,
        risk_tier=tier,
        tier_label=label,
    )
