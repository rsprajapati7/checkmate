from pydantic import BaseModel
class ReportData(BaseModel):
    id: str
    content: str
