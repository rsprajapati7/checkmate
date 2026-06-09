"""
Weighted Bayesian fusion engine.

Combines scores from all 4 forensic pipelines into a final 0-1 risk score.

Weights (configurable):
  ELA (pixel tampering):    0.35
  Metadata forensics:       0.25
  Seal analysis:            0.25
  NLP cross-document:       0.15
"""

from dataclasses import dataclass

from backend.core.models import RiskTier
from backend.fusion.weights import WEIGHT_ELA, WEIGHT_METADATA, WEIGHT_SEAL, WEIGHT_NLP
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

    Scanned document weights:  ELA=0.35, Meta=0.25, Seal=0.25, NLP=0.15
    Digital document weights:  ELA=0.20, Meta=0.45, Seal=0.15, NLP=0.20
    """
    # Normalize to 0-1
    ela_n = ela_score / 100.0
    meta_n = metadata_score / 100.0
    seal_n = seal_score / 100.0
    nlp_n = nlp_score / 100.0

    if is_scanned:
        w_ela = WEIGHT_ELA
        w_meta = WEIGHT_METADATA
        w_seal = WEIGHT_SEAL
        w_nlp = WEIGHT_NLP
    else:
        w_ela = 0.20
        w_meta = 0.45
        w_seal = 0.15
        w_nlp = 0.20

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
        f"[Fusion] ELA={ela_score:.1f} Meta={metadata_score:.1f} "
        f"Seal={seal_score:.1f} NLP={nlp_score:.1f} is_scanned={is_scanned} -> "
        f"Final={final:.3f} ({tier.value})"
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
