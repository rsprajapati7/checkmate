from pydantic import BaseModel
from typing import List, Dict, Any

class AnalysisResponse(BaseModel):
    document_id: str
    job_id: str
    status: str
