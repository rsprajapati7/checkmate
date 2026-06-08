"""Pydantic v2 schemas for risk scores and pipeline results."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class PipelineScores(BaseModel):
    ela: float
    metadata: float
    seal: float
    nlp: float


class RiskScoreSchema(BaseModel):
    job_id: str
    final_score: float
    risk_tier: str
    tier_label: str
    scores: PipelineScores
    ela_flags: List[str] = []
    metadata_flags: List[str] = []
    seal_flags: List[str] = []
    nlp_flags: List[str] = []
    pattern_flags: List[str] = []
    doc_type: Optional[str] = None
    extracted_fields: Dict[str, Any] = {}
    registry_verified: Optional[bool] = None
    ela_heatmap_b64: Optional[str] = None
    llm_investigation: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    message: str
