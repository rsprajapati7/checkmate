from sqlalchemy import Column, Integer, String, Float, JSON
from backend.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String)
