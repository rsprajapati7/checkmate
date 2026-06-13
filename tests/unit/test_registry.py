import pytest
from backend.core.config import settings
from backend.cross_analysis.registry_client import (
    verify_document,
    verify_aadhaar,
    verify_pan,
    verify_university,
    verify_certificate,
    verify_marksheet,
    init_registry_db,
)


@pytest.fixture(autouse=True)
def setup_test_registry_db(tmp_path):
    # Override registry DB path for tests
    old_path = settings.REGISTRY_DB_PATH
    test_db = tmp_path / "test_registry.db"
    settings.REGISTRY_DB_PATH = str(test_db)
    
    # Re-initialize the test database
    init_registry_db()
    
    yield
    
    # Restore configuration
    settings.REGISTRY_DB_PATH = old_path


def test_verify_aadhaar():
    # Test existing Aadhaar
    res = verify_aadhaar("234567890123")
    assert res.found is True
    assert res.match is True
    assert res.details["name"] == "Rajesh Kumar"
    
    # Test missing Aadhaar
    res = verify_aadhaar("000000000000")
    assert res.found is False
    assert res.match is False


def test_verify_pan():
    # Test active PAN
    res = verify_pan("ABCDE1234F")
    assert res.found is True
    assert res.match is True
    assert res.details["name"] == "Rajesh Kumar"
    assert res.details["status"] == "Active"

    # Test inactive PAN
    res = verify_pan("BBBBB8888B")
    assert res.found is True
    assert res.match is False  # match should be false if status != Active
    assert res.details["status"] == "Inactive"
    
    # Test missing PAN
    res = verify_pan("XXXXX9999X")
    assert res.found is False
    assert res.match is False


def test_verify_university():
    # Test UGC approved university (exact match)
    res = verify_university("University of Mumbai")
    assert res.found is True
    assert res.match is True
    
    # Test UGC approved university (substring match)
    res = verify_university("Mumbai")
    assert res.found is True
    assert res.match is True
    
    # Test unapproved/fake university
    res = verify_university("Pacific Ocean University")
    assert res.found is True
    assert res.match is False
    
    # Test missing university
    res = verify_university("Unverified Unknown Academy")
    assert res.found is False
    assert res.match is False


def test_verify_certificate():
    # Test valid certificate
    res = verify_certificate("CERT2024001")
    assert res.found is True
    assert res.match is True
    
    # Test invalid certificate
    res = verify_certificate("CERTFAKE001")
    assert res.found is True
    assert res.match is False
    
    # Test missing certificate
    res = verify_certificate("CERTNOTFOUND")
    assert res.found is False
    assert res.match is False


def test_verify_document_routing():
    # Test PAN routing
    res = verify_document("PAN", "ABCDE1234F")
    assert res is not None
    assert res.doc_type == "PAN"
    assert res.found is True

    # Test Aadhaar routing
    res = verify_document("Aadhaar", "234567890123")
    assert res is not None
    assert res.doc_type == "Aadhaar"
    assert res.found is True

    # Test marksheet routing
    res = verify_document("marksheet", "13615747")
    assert res is not None
    assert res.doc_type == "Marksheet"
    assert res.found is True

    # Test empty/None id routing
    res = verify_document("PAN", "")
    assert res is None


def test_verify_marksheet():
    # Valid roll number — no name check
    res = verify_marksheet("13615747")
    assert res.found is True
    assert res.match is True
    assert res.details["candidate"] == "RAJAT"
    assert res.details["school_no"] == "24219"

    # Valid roll number with correct names
    res = verify_marksheet("13615747", candidate="RAJAT", mother="BEENA", father="JAI SINGH")
    assert res.found is True
    assert res.match is True
    assert res.details["mismatches"] == []

    # Wrong candidate name — should flag as mismatch
    res = verify_marksheet("13615747", candidate="RAHUL")
    assert res.found is True
    assert res.match is False
    assert len(res.details["mismatches"]) == 1

    # Unknown roll number
    res = verify_marksheet("99999999")
    assert res.found is False
    assert res.match is False
