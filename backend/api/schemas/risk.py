from pydantic import BaseModel
from typing import List, Dict, Any

class RiskScore(BaseModel):
    score: float
    tier: str
    flags: List[str]
