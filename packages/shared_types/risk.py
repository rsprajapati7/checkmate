from pydantic import BaseModel
class RiskResult(BaseModel):
    score: float
    tier: str
