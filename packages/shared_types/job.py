from pydantic import BaseModel
class JobData(BaseModel):
    id: str
    status: str
