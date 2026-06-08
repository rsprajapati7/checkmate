"""
Mock registry client with seed data for Indian document verification.

Covers:
  - Aadhaar numbers (12-digit)
  - PAN numbers (ABCDE1234F format)
  - University / institution names
  - Certificate serial numbers

Pluggable: swap _REGISTRY with real API calls in production.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RegistryResult:
    found: bool
    match: bool
    doc_type: str
    details: dict = field(default_factory=dict)
    message: str = ""


# ---------------------------------------------------------------------------
# Seed Data
# ---------------------------------------------------------------------------

_AADHAAR_DB: Dict[str, dict] = {
    "234567890123": {"name": "Rajesh Kumar", "dob": "1985-03-12", "state": "Maharashtra"},
    "345678901234": {"name": "Priya Sharma", "dob": "1992-07-22", "state": "Delhi"},
    "456789012345": {"name": "Amit Singh", "dob": "1978-11-05", "state": "Uttar Pradesh"},
    "567890123456": {"name": "Sunita Devi", "dob": "1990-02-18", "state": "Bihar"},
    "678901234567": {"name": "Vikram Patel", "dob": "1988-09-30", "state": "Gujarat"},
    "789012345678": {"name": "Meena Krishnan", "dob": "1995-05-14", "state": "Tamil Nadu"},
    "890123456789": {"name": "Arjun Nair", "dob": "1982-12-01", "state": "Kerala"},
    "901234567890": {"name": "Deepika Reddy", "dob": "1998-04-25", "state": "Andhra Pradesh"},
}

_PAN_DB: Dict[str, dict] = {
    "ABCDE1234F": {"name": "Rajesh Kumar", "type": "Individual", "status": "Active"},
    "BCDEF2345G": {"name": "Priya Sharma", "type": "Individual", "status": "Active"},
    "CDEFG3456H": {"name": "Amit Singh", "type": "Individual", "status": "Active"},
    "DEFGH4567I": {"name": "Sunita Devi", "type": "Individual", "status": "Active"},
    "EFGHI5678J": {"name": "Vikram Patel", "type": "Individual", "status": "Active"},
    "FGHIJ6789K": {"name": "Meena Krishnan", "type": "Individual", "status": "Active"},
    "AAAAA9999A": {"name": "XYZ Corporation", "type": "Company", "status": "Active"},
    "BBBBB8888B": {"name": "ABC Traders", "type": "Firm", "status": "Inactive"},
}

_UNIVERSITY_DB: Dict[str, dict] = {
    "University of Mumbai": {"city": "Mumbai", "state": "Maharashtra", "ugc_approved": True},
    "Delhi University": {"city": "Delhi", "state": "Delhi", "ugc_approved": True},
    "IIT Bombay": {"city": "Mumbai", "state": "Maharashtra", "ugc_approved": True},
    "IIT Delhi": {"city": "Delhi", "state": "Delhi", "ugc_approved": True},
    "Anna University": {"city": "Chennai", "state": "Tamil Nadu", "ugc_approved": True},
    "Osmania University": {"city": "Hyderabad", "state": "Telangana", "ugc_approved": True},
    "Punjab University": {"city": "Chandigarh", "state": "Punjab", "ugc_approved": True},
    "Calcutta University": {"city": "Kolkata", "state": "West Bengal", "ugc_approved": True},
    "Bangalore University": {"city": "Bangalore", "state": "Karnataka", "ugc_approved": True},
    # Known fake universities
    "Pacific Ocean University": {"city": "Unknown", "state": "Unknown", "ugc_approved": False},
    "Global Education Institute": {"city": "Unknown", "state": "Unknown", "ugc_approved": False},
}

_CERTIFICATE_DB: Dict[str, dict] = {
    "CERT2024001": {"institution": "University of Mumbai", "valid": True, "year": 2024},
    "CERT2024002": {"institution": "IIT Bombay", "valid": True, "year": 2024},
    "CERT2023001": {"institution": "Delhi University", "valid": True, "year": 2023},
    "CERT2023002": {"institution": "Anna University", "valid": True, "year": 2023},
    "CERTFAKE001": {"institution": "Pacific Ocean University", "valid": False, "year": 2022},
    "CERTFAKE002": {"institution": "Global Education Institute", "valid": False, "year": 2023},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_aadhaar(aadhaar_number: str) -> RegistryResult:
    """Check if an Aadhaar number exists in the mock registry."""
    clean = aadhaar_number.replace(" ", "").strip()
    if clean in _AADHAAR_DB:
        data = _AADHAAR_DB[clean]
        return RegistryResult(
            found=True, match=True, doc_type="Aadhaar",
            details=data, message=f"Aadhaar verified for {data['name']}"
        )
    return RegistryResult(
        found=False, match=False, doc_type="Aadhaar",
        message=f"Aadhaar {clean} not found in registry"
    )


def verify_pan(pan_number: str) -> RegistryResult:
    """Check if a PAN number exists and is active."""
    clean = pan_number.upper().strip()
    if clean in _PAN_DB:
        data = _PAN_DB[clean]
        is_active = data.get("status") == "Active"
        return RegistryResult(
            found=True, match=is_active, doc_type="PAN",
            details=data,
            message=f"PAN {clean} found — {data['name']} (Status: {data['status']})"
        )
    return RegistryResult(
        found=False, match=False, doc_type="PAN",
        message=f"PAN {clean} not found in registry"
    )


def verify_university(university_name: str) -> RegistryResult:
    """Check if a university/institution exists and is UGC-approved."""
    # Case-insensitive search
    for name, data in _UNIVERSITY_DB.items():
        if name.lower() in university_name.lower() or university_name.lower() in name.lower():
            ugc = data.get("ugc_approved", False)
            return RegistryResult(
                found=True, match=ugc, doc_type="University",
                details=data,
                message=f"{'UGC-approved' if ugc else 'NOT UGC-approved'}: {name}"
            )
    return RegistryResult(
        found=False, match=False, doc_type="University",
        message=f"University '{university_name}' not found in registry"
    )


def verify_certificate(serial_number: str) -> RegistryResult:
    """Check if a certificate serial number is valid."""
    clean = serial_number.upper().strip()
    if clean in _CERTIFICATE_DB:
        data = _CERTIFICATE_DB[clean]
        return RegistryResult(
            found=True, match=data.get("valid", False), doc_type="Certificate",
            details=data,
            message=f"Certificate {clean}: {'VALID' if data.get('valid') else 'INVALID'}"
        )
    return RegistryResult(
        found=False, match=False, doc_type="Certificate",
        message=f"Certificate {clean} not found in registry"
    )


def verify_document(doc_type: str, id_number: str) -> Optional[RegistryResult]:
    """Route to the correct verifier based on doc_type."""
    # Coerce to string to handle int or Enum inputs gracefully
    doc_type = str(doc_type).lower().strip()
    id_number = str(id_number).strip()

    if not id_number or id_number in ("None", "none", ""):
        return None

    if "aadhaar" in doc_type:
        return verify_aadhaar(id_number)
    elif "pan" in doc_type:
        return verify_pan(id_number)
    elif "certificate" in doc_type or "degree" in doc_type or "marksheet" in doc_type:
        return verify_certificate(id_number)
    elif "university" in doc_type or "institution" in doc_type:
        return verify_university(id_number)
    return None