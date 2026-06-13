"""
Mock registry client with SQLite database file backend for Indian document verification.

Covers:
  - Aadhaar numbers (12-digit)
  - PAN numbers (ABCDE1234F format)
  - University / institution names
  - Certificate serial numbers

Pluggable: swap registry.db queries with real API calls in production.
"""

import os
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from backend.core.config import settings


@dataclass
class RegistryResult:
    found: bool
    match: bool
    doc_type: str
    details: dict = field(default_factory=dict)
    message: str = ""


# ---------------------------------------------------------------------------
# DB Connection & Initialization Helpers
# ---------------------------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the registry SQLite database."""
    conn = sqlite3.connect(settings.REGISTRY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_registry_db():
    """Create and seed the registry database tables if they do not exist or are empty."""
    # Ensure parent directories exist
    db_dir = os.path.dirname(os.path.abspath(settings.REGISTRY_DB_PATH))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Aadhaar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aadhaar (
                aadhaar_number TEXT PRIMARY KEY,
                name TEXT,
                dob TEXT,
                state TEXT
            )
        """)
        
        # 2. PAN
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pan (
                pan_number TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                status TEXT
            )
        """)
        
        # 3. University
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS university (
                name TEXT PRIMARY KEY,
                city TEXT,
                state TEXT,
                ugc_approved INTEGER
            )
        """)
        
        # 4. Certificate
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certificate (
                serial_number TEXT PRIMARY KEY,
                institution TEXT,
                valid INTEGER,
                year INTEGER
            )
        """)

        # 5. Marksheet (board exam results — QR cross-verification)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marksheet (
                roll_no   TEXT PRIMARY KEY,
                school_no TEXT,
                center_no TEXT,
                candidate TEXT,
                mother    TEXT,
                father    TEXT,
                sub1      TEXT,
                sub2      TEXT,
                sub3      TEXT,
                sub4      TEXT,
                sub5      TEXT,
                sub6      TEXT,
                sub7      TEXT,
                valid     INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        
        # Seed Aadhaar
        cursor.execute("SELECT COUNT(*) FROM aadhaar")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO aadhaar (aadhaar_number, name, dob, state) VALUES (?, ?, ?, ?)",
                [
                    ("234567890123", "Rajesh Kumar", "1985-03-12", "Maharashtra"),
                    ("345678901234", "Priya Sharma", "1992-07-22", "Delhi"),
                    ("456789012345", "Amit Singh", "1978-11-05", "Uttar Pradesh"),
                    ("567890123456", "Sunita Devi", "1990-02-18", "Bihar"),
                    ("678901234567", "Vikram Patel", "1988-09-30", "Gujarat"),
                    ("789012345678", "Meena Krishnan", "1995-05-14", "Tamil Nadu"),
                    ("890123456789", "Arjun Nair", "1982-12-01", "Kerala"),
                    ("901234567890", "Deepika Reddy", "1998-04-25", "Andhra Pradesh"),
                ]
            )
            
        # Seed PAN
        cursor.execute("SELECT COUNT(*) FROM pan")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO pan (pan_number, name, type, status) VALUES (?, ?, ?, ?)",
                [
                    ("ABCDE1234F", "Rajesh Kumar", "Individual", "Active"),
                    ("BCDEF2345G", "Priya Sharma", "Individual", "Active"),
                    ("CDEFG3456H", "Amit Singh", "Individual", "Active"),
                    ("DEFGH4567I", "Sunita Devi", "Individual", "Active"),
                    ("EFGHI5678J", "Vikram Patel", "Individual", "Active"),
                    ("FGHIJ6789K", "Meena Krishnan", "Individual", "Active"),
                    ("AAAAA9999A", "XYZ Corporation", "Company", "Active"),
                    ("BBBBB8888B", "ABC Traders", "Firm", "Inactive"),
                ]
            )
            
        # Seed University
        cursor.execute("SELECT COUNT(*) FROM university")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO university (name, city, state, ugc_approved) VALUES (?, ?, ?, ?)",
                [
                    ("University of Mumbai", "Mumbai", "Maharashtra", 1),
                    ("Delhi University", "Delhi", "Delhi", 1),
                    ("IIT Bombay", "Mumbai", "Maharashtra", 1),
                    ("IIT Delhi", "Delhi", "Delhi", 1),
                    ("Anna University", "Chennai", "Tamil Nadu", 1),
                    ("Osmania University", "Hyderabad", "Telangana", 1),
                    ("Punjab University", "Chandigarh", "Punjab", 1),
                    ("Calcutta University", "Kolkata", "West Bengal", 1),
                    ("Bangalore University", "Bangalore", "Karnataka", 1),
                    ("Pacific Ocean University", "Unknown", "Unknown", 0),
                    ("Global Education Institute", "Unknown", "Unknown", 0),
                ]
            )
            
        # Seed Certificate
        cursor.execute("SELECT COUNT(*) FROM certificate")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO certificate (serial_number, institution, valid, year) VALUES (?, ?, ?, ?)",
                [
                    ("CERT2024001", "University of Mumbai", 1, 2024),
                    ("CERT2024002", "IIT Bombay", 1, 2024),
                    ("CERT2023001", "Delhi University", 1, 2023),
                    ("CERT2023002", "Anna University", 1, 2023),
                    ("CERTFAKE001", "Pacific Ocean University", 0, 2022),
                    ("CERTFAKE002", "Global Education Institute", 0, 2023),
                ]
            )

        # Seed Marksheet (board exam results for cross-doc NLP testing)
        cursor.execute("SELECT COUNT(*) FROM marksheet")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                """INSERT INTO marksheet
                   (roll_no, school_no, center_no, candidate, mother, father,
                    sub1, sub2, sub3, sub4, sub5, sub6, sub7, valid)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    ("13615747", "24219", "816038", "RAJAT", "BEENA", "JAI SINGH",
                     "301", "302", "043", "041", "042", "", "", 1),
                ]
            )

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_aadhaar(aadhaar_number: str) -> RegistryResult:
    """Check if an Aadhaar number exists in the mock registry SQLite DB."""
    clean = str(aadhaar_number).replace(" ", "").strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM aadhaar WHERE aadhaar_number = ?", (clean,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            details = {
                "name": data["name"],
                "dob": data["dob"],
                "state": data["state"]
            }
            return RegistryResult(
                found=True, match=True, doc_type="Aadhaar",
                details=details, message=f"Aadhaar verified for {details['name']}"
            )
        return RegistryResult(
            found=False, match=False, doc_type="Aadhaar",
            message=f"Aadhaar {clean} not found in registry"
        )
    finally:
        conn.close()


def verify_pan(pan_number: str) -> RegistryResult:
    """Check if a PAN number exists and is active in SQLite DB."""
    clean = str(pan_number).upper().strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pan WHERE pan_number = ?", (clean,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            details = {
                "name": data["name"],
                "type": data["type"],
                "status": data["status"]
            }
            is_active = details.get("status") == "Active"
            return RegistryResult(
                found=True, match=is_active, doc_type="PAN",
                details=details,
                message=f"PAN {clean} found — {details['name']} (Status: {details['status']})"
            )
        return RegistryResult(
            found=False, match=False, doc_type="PAN",
            message=f"PAN {clean} not found in registry"
        )
    finally:
        conn.close()


def verify_university(university_name: str) -> RegistryResult:
    """Check if a university/institution exists and is UGC-approved in SQLite DB."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM university")
        rows = cursor.fetchall()
        for row in rows:
            data = dict(row)
            name = data["name"]
            if name.lower() in university_name.lower() or university_name.lower() in name.lower():
                ugc = bool(data["ugc_approved"])
                details = {
                    "city": data["city"],
                    "state": data["state"],
                    "ugc_approved": ugc
                }
                return RegistryResult(
                    found=True, match=ugc, doc_type="University",
                    details=details,
                    message=f"{'UGC-approved' if ugc else 'NOT UGC-approved'}: {name}"
                )
        return RegistryResult(
            found=False, match=False, doc_type="University",
            message=f"University '{university_name}' not found in registry"
        )
    finally:
        conn.close()


def verify_marksheet(roll_no: str, candidate: str = "", mother: str = "", father: str = "") -> RegistryResult:
    """
    Cross-check a board marksheet against the registry.

    Looks up by roll_no. If found, optionally validates candidate/mother/father
    names extracted from the document against the stored values.
    """
    clean_roll = str(roll_no).strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM marksheet WHERE roll_no = ?", (clean_roll,))
        row = cursor.fetchone()
        if not row:
            return RegistryResult(
                found=False, match=False, doc_type="Marksheet",
                message=f"Roll No {clean_roll} not found in board registry"
            )

        data = dict(row)
        mismatches: List[str] = []

        def _name_match(extracted: str, stored: str) -> bool:
            e = extracted.strip().upper()
            s = stored.strip().upper()
            return not e or e in s or s in e

        if candidate and not _name_match(candidate, data["candidate"]):
            mismatches.append(f"Candidate: got '{candidate}', registry has '{data['candidate']}'")
        if mother and not _name_match(mother, data["mother"]):
            mismatches.append(f"Mother: got '{mother}', registry has '{data['mother']}'")
        if father and not _name_match(father, data["father"]):
            mismatches.append(f"Father: got '{father}', registry has '{data['father']}'")

        valid = bool(data["valid"]) and not mismatches
        details = {
            "roll_no": data["roll_no"],
            "school_no": data["school_no"],
            "center_no": data["center_no"],
            "candidate": data["candidate"],
            "mother": data["mother"],
            "father": data["father"],
            "mismatches": mismatches,
        }
        msg = (
            f"Roll No {clean_roll} VERIFIED — {data['candidate']}"
            if valid
            else f"Roll No {clean_roll} MISMATCH — {'; '.join(mismatches) or 'record invalid'}"
        )
        return RegistryResult(found=True, match=valid, doc_type="Marksheet", details=details, message=msg)
    finally:
        conn.close()


def verify_certificate(serial_number: str) -> RegistryResult:
    """Check if a certificate serial number is valid in SQLite DB."""
    clean = str(serial_number).upper().strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM certificate WHERE serial_number = ?", (clean,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            valid = bool(data["valid"])
            details = {
                "institution": data["institution"],
                "valid": valid,
                "year": data["year"]
            }
            return RegistryResult(
                found=True, match=valid, doc_type="Certificate",
                details=details,
                message=f"Certificate {clean}: {'VALID' if valid else 'INVALID'}"
            )
        return RegistryResult(
            found=False, match=False, doc_type="Certificate",
            message=f"Certificate {clean} not found in registry"
        )
    finally:
        conn.close()


def verify_document(doc_type: str, id_number: str) -> Optional[RegistryResult]:
    """Route to the correct verifier based on doc_type."""
    doc_type = str(doc_type).lower().strip()
    id_number = str(id_number).strip()

    if not id_number or id_number in ("None", "none", ""):
        return None

    if "aadhaar" in doc_type:
        return verify_aadhaar(id_number)
    elif "pan" in doc_type:
        return verify_pan(id_number)
    elif "marksheet" in doc_type or "result" in doc_type or "board" in doc_type:
        return verify_marksheet(id_number)
    elif "certificate" in doc_type or "degree" in doc_type:
        return verify_certificate(id_number)
    elif "university" in doc_type or "institution" in doc_type:
        return verify_university(id_number)
    return None


# Auto-initialize the DB when importing this module
init_registry_db()