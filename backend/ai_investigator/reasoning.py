"""
Reasoning module — interprets LLM JSON responses into typed Pydantic models.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DocIdentificationResult:
    doc_type: str = "Other"
    confidence: float = 0.0
    issuing_authority: Optional[str] = None
    detected_id_numbers: List[str] = field(default_factory=list)
    language: str = "en"
    is_official_document: bool = False


@dataclass
class FieldNormalizationResult:
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    issuing_authority: Optional[str] = None
    father_name: Optional[str] = None
    gender: Optional[str] = None
    additional_fields: Dict[str, str] = field(default_factory=dict)


@dataclass
class PatternDetectionResult:
    reuse_detected: bool = False
    campaign_suspected: bool = False
    confidence: float = 0.0
    pattern_flags: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class InvestigationResult:
    verdict: str = "INSUFFICIENT_EVIDENCE"
    confidence: float = 0.0
    primary_tampering_method: Optional[str] = None
    key_evidence: List[str] = field(default_factory=list)
    risk_explanation: str = ""
    recommended_action: str = "MANUAL_REVIEW"


def parse_doc_identification(raw: dict) -> DocIdentificationResult:
    return DocIdentificationResult(
        doc_type=raw.get("doc_type", "Other"),
        confidence=float(raw.get("confidence", 0.0)),
        issuing_authority=raw.get("issuing_authority"),
        detected_id_numbers=raw.get("detected_id_numbers", []),
        language=raw.get("language", "en"),
        is_official_document=bool(raw.get("is_official_document", False)),
    )


def parse_field_normalization(raw: dict) -> FieldNormalizationResult:
    return FieldNormalizationResult(
        name=raw.get("name"),
        date_of_birth=raw.get("date_of_birth"),
        id_number=raw.get("id_number"),
        address=raw.get("address"),
        issue_date=raw.get("issue_date"),
        expiry_date=raw.get("expiry_date"),
        issuing_authority=raw.get("issuing_authority"),
        father_name=raw.get("father_name"),
        gender=raw.get("gender"),
        additional_fields=raw.get("additional_fields", {}),
    )


def parse_pattern_detection(raw: dict) -> PatternDetectionResult:
    return PatternDetectionResult(
        reuse_detected=bool(raw.get("reuse_detected", False)),
        campaign_suspected=bool(raw.get("campaign_suspected", False)),
        confidence=float(raw.get("confidence", 0.0)),
        pattern_flags=raw.get("pattern_flags", []),
        explanation=raw.get("explanation", ""),
    )


def parse_investigation(raw: dict) -> InvestigationResult:
    return InvestigationResult(
        verdict=raw.get("verdict", "INSUFFICIENT_EVIDENCE"),
        confidence=float(raw.get("confidence", 0.0)),
        primary_tampering_method=raw.get("primary_tampering_method"),
        key_evidence=raw.get("key_evidence", []),
        risk_explanation=raw.get("risk_explanation", ""),
        recommended_action=raw.get("recommended_action", "MANUAL_REVIEW"),
    )
