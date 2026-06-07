from pydantic import BaseModel
class DocumentMetadata(BaseModel):
    filename: str
    size: int
    content_type: str
