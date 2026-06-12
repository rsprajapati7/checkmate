from backend.ai_investigator.reasoning import (
    parse_doc_identification,
    parse_field_normalization,
    parse_pattern_detection,
    parse_investigation,
    DocIdentificationResult,
    FieldNormalizationResult,
    PatternDetectionResult,
    InvestigationResult,
)


def test_parse_doc_identification():
    raw = {
        "doc_type": "PAN",
        "confidence": 0.95,
        "issuing_authority": "Income Tax Department",
        "detected_id_numbers": ["ABCDE1234F"],
        "language": "en",
        "is_official_document": True,
    }
    res = parse_doc_identification(raw)
    assert isinstance(res, DocIdentificationResult)
    assert res.doc_type == "PAN"
    assert res.confidence == 0.95
    assert res.issuing_authority == "Income Tax Department"
    assert res.detected_id_numbers == ["ABCDE1234F"]
    assert res.language == "en"
    assert res.is_official_document is True


def test_parse_doc_identification_missing_fields():
    raw = {}
    res = parse_doc_identification(raw)
    assert isinstance(res, DocIdentificationResult)
    assert res.doc_type == "Other"
    assert res.confidence == 0.0
    assert res.issuing_authority is None
    assert res.detected_id_numbers == []
    assert res.language == "en"
    assert res.is_official_document is False


def test_parse_field_normalization():
    raw = {
        "name": "Jane Doe",
        "date_of_birth": "1990-01-01",
        "id_number": "1234-5678-9012",
        "address": "123 Main St",
        "issue_date": "2020-05-15",
        "expiry_date": "2030-05-15",
        "issuing_authority": "UIDAI",
        "father_name": "John Doe",
        "gender": "Female",
        "additional_fields": {"status": "active"},
    }
    res = parse_field_normalization(raw)
    assert isinstance(res, FieldNormalizationResult)
    assert res.name == "Jane Doe"
    assert res.date_of_birth == "1990-01-01"
    assert res.id_number == "1234-5678-9012"
    assert res.address == "123 Main St"
    assert res.issue_date == "2020-05-15"
    assert res.expiry_date == "2030-05-15"
    assert res.issuing_authority == "UIDAI"
    assert res.father_name == "John Doe"
    assert res.gender == "Female"
    assert res.additional_fields == {"status": "active"}


def test_parse_field_normalization_missing_fields():
    raw = {}
    res = parse_field_normalization(raw)
    assert isinstance(res, FieldNormalizationResult)
    assert res.name is None
    assert res.id_number is None
    assert res.additional_fields == {}


def test_parse_pattern_detection():
    raw = {
        "reuse_detected": True,
        "campaign_suspected": True,
        "confidence": 0.85,
        "pattern_flags": ["MULTIPLE_REUSE"],
        "explanation": "Same ID used across multiple applications",
    }
    res = parse_pattern_detection(raw)
    assert isinstance(res, PatternDetectionResult)
    assert res.reuse_detected is True
    assert res.campaign_suspected is True
    assert res.confidence == 0.85
    assert res.pattern_flags == ["MULTIPLE_REUSE"]
    assert res.explanation == "Same ID used across multiple applications"


def test_parse_pattern_detection_missing_fields():
    raw = {}
    res = parse_pattern_detection(raw)
    assert isinstance(res, PatternDetectionResult)
    assert res.reuse_detected is False
    assert res.campaign_suspected is False
    assert res.confidence == 0.0
    assert res.pattern_flags == []
    assert res.explanation == ""


def test_parse_investigation():
    raw = {
        "verdict": "SUSPICIOUS",
        "confidence": 0.9,
        "primary_tampering_method": "Font mismatch",
        "key_evidence": ["Name font differs from standard template"],
        "risk_explanation": "The document name field was altered using a different font.",
        "recommended_action": "REJECT",
    }
    res = parse_investigation(raw)
    assert isinstance(res, InvestigationResult)
    assert res.verdict == "SUSPICIOUS"
    assert res.confidence == 0.9
    assert res.primary_tampering_method == "Font mismatch"
    assert res.key_evidence == ["Name font differs from standard template"]
    assert res.risk_explanation == "The document name field was altered using a different font."
    assert res.recommended_action == "REJECT"


def test_parse_investigation_missing_fields():
    raw = {}
    res = parse_investigation(raw)
    assert isinstance(res, InvestigationResult)
    assert res.verdict == "INSUFFICIENT_EVIDENCE"
    assert res.confidence == 0.0
    assert res.primary_tampering_method is None
    assert res.key_evidence == []
    assert res.risk_explanation == ""
    assert res.recommended_action == "MANUAL_REVIEW"