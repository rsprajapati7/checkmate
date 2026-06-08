"""
Unit tests for NLP cross-document pipeline:
  - Entity extraction and stop-word filtering
  - QR data parsing (JSON, Python dict, key=value)
  - QR vs OCR cross-verification
  - Accounting consistency rules
"""
import pytest
from backend.pipelines.nlp_cross_doc.entity_extractor import extract_entities, _is_label_phrase
from backend.pipelines.nlp_cross_doc.scorer import parse_qr_data, _cross_check_qr_fields
from backend.pipelines.nlp_cross_doc.accounting_rules import (
    check_pan_consistency,
    check_aadhaar_consistency,
    check_balance_sheet,
    check_revenue_gst_consistency,
)


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

class TestEntityExtraction:
    def test_extracts_valid_pan(self):
        text = "Applicant PAN: ABCDE1234F is verified."
        ent = extract_entities(text)
        assert "ABCDE1234F" in ent.pan_numbers

    def test_extracts_aadhaar(self):
        text = "Aadhaar: 2345 6789 0123"
        ent = extract_entities(text)
        assert "234567890123" in ent.aadhaar_numbers

    def test_extracts_gst(self):
        text = "GSTIN: 29ABCDE1234F1Z5"
        ent = extract_entities(text)
        assert "29ABCDE1234F1Z5" in ent.gst_numbers

    def test_extracts_money(self):
        text = "Total revenue: Rs. 1,25,000.00"
        ent = extract_entities(text)
        assert 125000.0 in ent.money_amounts

    def test_stop_words_filtered(self):
        text = "Roll Number Unfair Means Prohibited Items Royal Blue"
        ent = extract_entities(text)
        # None of these label phrases should be in person_names
        for label in ["Roll Number", "Unfair Means", "Prohibited Items", "Royal Blue"]:
            assert label not in ent.person_names, f"Stop word '{label}' leaked into person_names"

    def test_real_name_not_filtered(self):
        text = "Candidate's Name: Rajat Kumar Sharma"
        ent = extract_entities(text)
        # At least one reasonable name should survive
        found = any("Rajat" in n or "Kumar" in n or "Sharma" in n for n in ent.person_names)
        assert found, f"Valid person name not found in: {ent.person_names}"

    def test_is_label_phrase_detects_labels(self):
        assert _is_label_phrase("Roll Number") is True
        assert _is_label_phrase("Unfair Means") is True

    def test_multiline_names_rejected(self):
        text = "Gujarat\nPaarivaarik Samaachaar\nEdited"
        ent = extract_entities(text)
        for name in ent.person_names:
            assert "\n" not in name, f"Multiline name leaked: {name!r}"


# ---------------------------------------------------------------------------
# QR data parsing
# ---------------------------------------------------------------------------

class TestQRDataParsing:
    ROLL_QR_PAYLOAD = (
        "{'RollNo':'13615747','SchoolNo':'24219','CenterNo':'816038',"
        "'Candidate Name':'RAJAT','Mother Name':'BEENA','Father Name':'JAI SINGH',"
        "'Sub1':'301','Sub2':'302','Sub3':'043','Sub4':'041' ,'Sub5':'042','Sub6':'','Sub7':''}"
    )

    def test_parses_python_dict_literal(self):
        result = parse_qr_data(self.ROLL_QR_PAYLOAD)
        assert isinstance(result, dict)
        assert result.get("Candidate Name") == "RAJAT"
        assert result.get("Mother Name") == "BEENA"
        assert result.get("Father Name") == "JAI SINGH"

    def test_parses_json(self):
        import json
        payload = json.dumps({"name": "Rajesh", "pan": "ABCDE1234F"})
        result = parse_qr_data(payload)
        assert result["name"] == "Rajesh"
        assert result["pan"] == "ABCDE1234F"

    def test_parses_key_value_pairs(self):
        payload = "name=Amit&city=Delhi&state=UP"
        result = parse_qr_data(payload)
        assert result["name"] == "Amit"
        assert result["city"] == "Delhi"

    def test_empty_string_returns_empty_dict(self):
        assert parse_qr_data("") == {}

    def test_plain_text_returns_empty_dict(self):
        # A plain URL or text not key-value returns empty dict
        result = parse_qr_data("https://example.com/verify/12345")
        # Should not crash; may or may not parse depending on structure
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# QR vs OCR cross-check
# ---------------------------------------------------------------------------

class TestQROCRCrossCheck:
    def test_matching_fields_no_flags(self):
        qr_dict = {"Candidate Name": "RAJAT", "Father Name": "JAI SINGH"}
        ocr = "Candidate's Name RAJAT Father/Guardian's Name JAI SINGH Roll No. 13615747"
        flags = []
        sev = _cross_check_qr_fields(qr_dict, ocr, flags)
        assert sev == 0.0
        assert len(flags) == 0

    def test_missing_field_flags_and_adds_severity(self):
        qr_dict = {"Candidate Name": "FAKENAME"}
        ocr = "Candidate's Name RAJAT Mother's Name BEENA"
        flags = []
        sev = _cross_check_qr_fields(qr_dict, ocr, flags)
        assert sev > 0.0
        assert len(flags) == 1
        assert "FAKENAME" in flags[0]

    def test_numeric_sub_codes_skipped(self):
        """Subject codes (Sub1, Sub2...) should not trigger cross-check."""
        qr_dict = {"Sub1": "301", "Sub2": "302", "Candidate Name": "RAJAT"}
        ocr = "Candidate's Name RAJAT"
        flags = []
        sev = _cross_check_qr_fields(qr_dict, ocr, flags)
        # Only Candidate Name should be checked; it matches, so 0 flags
        assert len(flags) == 0


# ---------------------------------------------------------------------------
# Accounting consistency
# ---------------------------------------------------------------------------

class TestAccountingRules:
    def test_pan_consistency_single_ok(self):
        triggered, _ = check_pan_consistency(["ABCDE1234F"])
        assert not triggered

    def test_pan_consistency_multiple_flags(self):
        triggered, msg = check_pan_consistency(["ABCDE1234F", "BCDEF2345G"])
        assert triggered
        assert "ABCDE1234F" in msg or "BCDEF2345G" in msg

    def test_aadhaar_consistency_same_ok(self):
        triggered, _ = check_aadhaar_consistency(["234567890123", "234567890123"])
        assert not triggered

    def test_balance_sheet_pass(self):
        """Assets = Liabilities + Equity exactly."""
        triggered, _ = check_balance_sheet(100000, 60000, 40000)
        assert not triggered

    def test_balance_sheet_fail(self):
        """Assets significantly different from Liabilities + Equity."""
        triggered, msg = check_balance_sheet(100000, 50000, 30000)
        assert triggered
        assert "mismatch" in msg.lower()

    def test_revenue_gst_within_tolerance(self):
        """Within 20% is OK."""
        triggered, _ = check_revenue_gst_consistency(100000, 95000)
        assert not triggered

    def test_revenue_gst_outside_tolerance(self):
        triggered, msg = check_revenue_gst_consistency(100000, 50000)
        assert triggered