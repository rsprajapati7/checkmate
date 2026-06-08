"""
Entity extractor — uses regex to find Indian document identifiers and financial values.

Extracted entities:
  - PAN number (ABCDE1234F)
  - Aadhaar number (12 digits, spaced or unspaced)
  - GST number (15 chars GSTIN)
  - Dates (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)
  - Money amounts (rupee values with commas)
  - Person names (capitalized multi-word sequences, noise-filtered)
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ExtractedEntities:
    pan_numbers: List[str] = field(default_factory=list)
    aadhaar_numbers: List[str] = field(default_factory=list)
    gst_numbers: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    money_amounts: List[float] = field(default_factory=list)   # normalized to float
    person_names: List[str] = field(default_factory=list)
    raw_text: str = ""


# Regex patterns
_PAN_RE = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')
_AADHAAR_RE = re.compile(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b')
_GST_RE = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b')
_DATE_RE = re.compile(
    r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b'
)
_MONEY_RE = re.compile(r'(?:Rs\.?|INR|₹)\s?([\d,]+(?:\.\d{1,2})?)')
_CAPS_NAME_RE = re.compile(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,4})\b')


# Comprehensive stop-words list covering document labels, exam-card phrases,
# government terminology, and common OCR artifacts.
_STOP_WORDS = {
    # Government / generic
    "Government", "Ministry", "Department", "Republic", "India", "Authority",
    "National", "State", "District", "Board", "Council", "Commission",
    "Director", "Directorate", "Office", "Bureau", "Division",
    # Exam / admit card specific
    "Roll Number", "Roll No", "Centre No", "Centre Number", "School No",
    "Admit Card", "Candidate Name", "Candidates Name", "Mother Name",
    "Father Name", "Guardian Name", "Date Birth", "Date Of Birth",
    "Examination", "Senior Secondary", "Secondary", "Subject Code",
    "Subject Name", "Unfair Means", "Materials Mobile", "Prohibited Items",
    "Permitted Stationery", "Important Instructions", "Centre Superintendent",
    "Invigilator", "Royal Blue",
    # Financial / legal
    "Balance Sheet", "Profit Loss", "Net Profit", "Gross Profit",
    "Current Assets", "Fixed Assets", "Total Assets", "Total Liabilities",
    # Document labels
    "Signature", "Photograph", "Thumb Impression", "Seal Stamp",
    "Issue Date", "Expiry Date", "Valid Till", "Not Applicable",
    # Educational
    "Fine Arts", "Senior Editor", "Publishing", "Arts Completed",
    "College", "University",
}


def _normalize_amount(raw: str) -> float:
    """Remove commas and convert to float."""
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return 0.0


def _normalize_aadhaar(raw: str) -> str:
    """Strip spaces from Aadhaar for comparison."""
    return re.sub(r'\s', '', raw)


# Common generic document-label suffix words that make a phrase a label, not a name
_LABEL_WORDS = {
    "Number", "No", "Code", "Date", "Card", "Address", "Id", "Type",
    "Name", "Status", "Means", "Items", "Stationery", "Superintendent",
    "Marks", "Score", "Result", "Certificate", "Details", "Sheet",
    "Statement", "Declaration", "Signature", "Photograph", "Thumb",
    "Impression", "Category", "Centre", "Center", "Exam", "Examination",
}


def _is_label_phrase(name: str) -> bool:
    """Return True if the name looks like a document label rather than a person name."""
    words = name.split()
    if len(words) >= 2:
        # Check if majority of words are stop-words or label-words
        noise_hits = sum(
            1 for w in words
            if w in _STOP_WORDS or w in _LABEL_WORDS or len(w) <= 2
        )
        if noise_hits >= len(words) - 1:
            return True
    return False


def extract_entities(text: str) -> ExtractedEntities:
    """Extract all relevant entities from an OCR text block."""
    ent = ExtractedEntities(raw_text=text)

    ent.pan_numbers = list(set(_PAN_RE.findall(text)))
    aadhaar_raw = _AADHAAR_RE.findall(text)
    ent.aadhaar_numbers = list(set(_normalize_aadhaar(a) for a in aadhaar_raw))
    ent.gst_numbers = list(set(_GST_RE.findall(text)))
    ent.dates = list(set(_DATE_RE.findall(text)))

    money_raw = _MONEY_RE.findall(text)
    ent.money_amounts = [_normalize_amount(m) for m in money_raw if _normalize_amount(m) > 0]

    # Filter caps names — avoid PAN-like strings, stop-word phrases, and label phrases
    names_raw = _CAPS_NAME_RE.findall(text)
    ent.person_names = [
        n for n in set(names_raw)
        if n not in _STOP_WORDS
        and not _PAN_RE.match(n)
        and not _is_label_phrase(n)
        and "\n" not in n          # reject multi-line OCR artifacts
        and len(n.split()) <= 4    # max 4-word names
    ]

    return ent
