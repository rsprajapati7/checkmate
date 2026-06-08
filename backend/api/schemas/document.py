"""Pydantic v2 schemas for document upload and metadata."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentUpload(BaseModel):
    filename: str
    file_type: str
    file_size_bytes: int


class DocumentMetadata(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    is_scanned: bool
    page_count: int
    created_at: datetime

    class Config:
        from_attributes = True
