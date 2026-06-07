from pydantic import BaseModel
class DocumentData(BaseModel):
    id: str
    name: str
