"""
Campaign detector — finds coordinated fraud patterns across documents.

Combines:
  1. Historical DB lookup for reused ID numbers
  2. Gemma 4 pattern analysis prompt (for deeper reasoning)
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

from backend.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PatternResult:
    reuse_detected: bool = False
    campaign_suspected: bool = False
    confidence: float = 0.0
    pattern_flags: List[str] = field(default_factory=list)
    explanation: str = ""


async def run_pattern_detection(
    current_entities: dict,
    historical_matches: List[dict],
    use_llm: bool = True,
) -> PatternResult:
    """
    Run pattern detection using historical DB comparison and optional LLM reasoning.

    Parameters
    ----------
    current_entities : dict
        Entity summary from NLP pipeline (PAN, Aadhaar, etc.)
    historical_matches : list[dict]
        Previous docs with overlapping IDs from HistoricalEntry table
    use_llm : bool
        Whether to invoke Gemma 4 for deeper pattern analysis
    """
    flags: List[str] = []
    reuse_detected = False
    campaign_suspected = False
    confidence = 0.0

    # --- Rule-based pattern checks ---
    pan_numbers = current_entities.get("pan_numbers", [])
    aadhaar_numbers = current_entities.get("aadhaar_numbers", [])

    if historical_matches:
        reuse_detected = True
        flags.append(
            f"ID numbers from this document appear in {len(historical_matches)} previously processed documents"
        )

        # Check if any historical doc was flagged RED
        red_count = sum(1 for m in historical_matches if m.get("risk_tier") == "RED")
        if red_count > 0:
            campaign_suspected = True
            confidence = min(0.95, 0.6 + red_count * 0.1)
            flags.append(f"{red_count} of the matching historical documents were flagged as HIGH RISK")

        # Check rapid reuse (multiple docs within short timeframe)
        if len(historical_matches) >= 3:
            campaign_suspected = True
            confidence = max(confidence, 0.75)
            flags.append(f"Same identifiers used in {len(historical_matches)} documents — possible campaign")

    # --- LLM Pattern Analysis ---
    if use_llm and (historical_matches or len(pan_numbers) > 0):
        try:
            llm_result = await _llm_pattern_check(current_entities, historical_matches)
            if llm_result.reuse_detected:
                reuse_detected = True
            if llm_result.campaign_suspected:
                campaign_suspected = True
            confidence = max(confidence, llm_result.confidence)
            flags.extend(llm_result.pattern_flags)
            explanation = llm_result.explanation
        except Exception as e:
            logger.warning(f"[Pattern] LLM pattern check failed: {e}")
            explanation = "LLM analysis unavailable"
    else:
        explanation = "No historical matches found" if not historical_matches else "Pattern detected via rule-based analysis"

    return PatternResult(
        reuse_detected=reuse_detected,
        campaign_suspected=campaign_suspected,
        confidence=confidence,
        pattern_flags=list(set(flags)),
        explanation=explanation,
    )


async def _llm_pattern_check(current_entities: dict, historical_matches: List[dict]):
    """Use Gemma 4 to reason about fraud patterns."""
    from backend.ai_investigator.llm_client import llm_client
    from backend.ai_investigator.prompt_builder import build_pattern_detection_prompt
    from backend.ai_investigator.reasoning import parse_pattern_detection

    prompt = build_pattern_detection_prompt(current_entities, historical_matches)
    raw = await llm_client.complete_json(prompt)
    return parse_pattern_detection(raw)