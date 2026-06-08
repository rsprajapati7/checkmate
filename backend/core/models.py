import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Enum as SAEnum,
    Text, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class RiskTier(str, enum.Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    UNKNOWN = "UNKNOWN"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    INGESTING = "INGESTING"
    ANALYZING = "ANALYZING"
    FUSING = "FUSING"
    INVESTIGATING = "INVESTIGATING"
    REPORTING = "REPORTING"
    DONE = "DONE"
    FAILED = "FAILED"


def _uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    file_type = Column(String)           # "PDF" | "PNG" | "JPG"
    is_scanned = Column(Boolean, default=False)
    page_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="document")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING)
    stage = Column(String, default="queued")
    progress = Column(Integer, default=0)       # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="jobs")
    risk_score = relationship("RiskScore", back_populates="job", uselist=False)
    report = relationship("Report", back_populates="job", uselist=False)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), unique=True, nullable=False)

    # Per-pipeline scores (0-100 normalized)
    ela_score = Column(Float, default=0.0)
    metadata_score = Column(Float, default=0.0)
    seal_score = Column(Float, default=0.0)
    nlp_score = Column(Float, default=0.0)

    # Final fused score (0-1)
    final_score = Column(Float, default=0.0)
    risk_tier = Column(SAEnum(RiskTier), default=RiskTier.UNKNOWN)

    # Per-pipeline flags (list of strings)
    ela_flags = Column(JSON, default=list)
    metadata_flags = Column(JSON, default=list)
    seal_flags = Column(JSON, default=list)
    nlp_flags = Column(JSON, default=list)

    # ELA heatmap base64 image
    ela_heatmap_b64 = Column(Text, nullable=True)

    # Doc classification
    doc_type = Column(String, nullable=True)     # Aadhaar / PAN / Certificate / etc.
    extracted_fields = Column(JSON, default=dict)

    # Registry check result
    registry_verified = Column(Boolean, nullable=True)
    registry_details = Column(JSON, default=dict)

    # Pattern detection
    pattern_flags = Column(JSON, default=list)

    # LLM investigation summary (RED only)
    llm_investigation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="risk_score")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), unique=True, nullable=False)
    pdf_path = Column(String, nullable=True)
    html_path = Column(String, nullable=True)
    json_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="report")


class HistoricalEntry(Base):
    """Records processed document fingerprints for cross-document pattern detection."""
    __tablename__ = "historical_entries"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    doc_type = Column(String, nullable=True)
    id_numbers = Column(JSON, default=list)      # PAN, Aadhaar, GST etc.
    name_hash = Column(String, nullable=True)    # SHA256 of normalized name
    seal_hash = Column(String, nullable=True)    # Perceptual hash of seal region
    risk_tier = Column(SAEnum(RiskTier), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
