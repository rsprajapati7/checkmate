"""
Prompt builder for all 4 Gemma 4 stages.

Stage 1 — Document Identification:
  Input: OCR text + QR data
  Output: { doc_type, confidence, detected_id_numbers, issuing_authority }

Stage 2 — Field Normalization:
  Input: OCR text + doc_type
  Output: { fields: { name, dob, id_number, ... }, schema_version }

Stage 3 — Pattern Detection:
  Input: entities from current doc + historical summary
  Output: { reuse_detected, cross_doc_anomalies, confidence }

Stage 4 — Deep AI Investigation (RED tier only):
  Input: all pipeline scores + flags + ELA heatmap image
  Output: { verdict, evidence, anomalies, confidence, explanation }
"""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Stage 1: Document Identification
# ---------------------------------------------------------------------------

def build_doc_identification_prompt(ocr_text: str, qr_data: List[str]) -> str:
    qr_section = "\n".join(f"- {q}" for q in qr_data) if qr_data else "None detected"
    return f"""You are a document forensics expert specializing in Indian government-issued documents.

Analyze the following document text and QR code data, then classify the document.

OCR TEXT:
\"\"\"
{ocr_text[:3000]}
\"\"\"

QR CODE DATA:
{qr_section}

Respond with a JSON object in this exact format:
{{
  "doc_type": "<one of: Aadhaar, PAN, Passport, DrivingLicense, VoterID, BirthCertificate, DegreeCertificate, BankStatement, ITR, GST, Marksheet, Other>",
  "confidence": <0.0 to 1.0>,
  "issuing_authority": "<name of issuing body or null>",
  "detected_id_numbers": ["<ID numbers visible in document>"],
  "language": "<primary language detected>",
  "is_official_document": <true or false>
}}"""


# ---------------------------------------------------------------------------
# Stage 2: Field Normalization
# ---------------------------------------------------------------------------

def build_field_normalization_prompt(ocr_text: str, doc_type: str) -> str:
    return f"""You are a document data extraction expert.

Extract and normalize structured fields from this {doc_type} document.

OCR TEXT:
\"\"\"
{ocr_text[:4000]}
\"\"\"

Extract all available fields and return them in this JSON format:
{{
  "name": "<full name of person or null>",
  "date_of_birth": "<YYYY-MM-DD or null>",
  "id_number": "<primary ID number or null>",
  "address": "<full address or null>",
  "issue_date": "<YYYY-MM-DD or null>",
  "expiry_date": "<YYYY-MM-DD or null>",
  "issuing_authority": "<authority name or null>",
  "father_name": "<father name or null>",
  "gender": "<Male/Female/Other or null>",
  "additional_fields": {{
    "<field_name>": "<value>"
  }}
}}

Return null for any field not found. Do not guess or hallucinate values."""


# ---------------------------------------------------------------------------
# Stage 3: Pattern Detection
# ---------------------------------------------------------------------------

def build_pattern_detection_prompt(
    current_entities: dict,
    historical_matches: List[dict],
) -> str:
    hist_text = "\n".join(
        f"- Doc #{i+1}: type={m.get('doc_type')}, IDs={m.get('id_numbers')}, tier={m.get('risk_tier')}, date={m.get('created_at')}"
        for i, m in enumerate(historical_matches[:10])
    ) or "No historical matches found"

    return f"""You are a fraud pattern analysis expert.

Current document entities:
{current_entities}

Historical documents with overlapping identifiers:
{hist_text}

Analyze for coordinated fraud patterns:
1. Are the same ID numbers reused across different documents suspiciously?
2. Are there timing anomalies (documents issued too close together)?
3. Do the document types form a suspicious combination?

Return a JSON object:
{{
  "reuse_detected": <true or false>,
  "campaign_suspected": <true or false>,
  "confidence": <0.0 to 1.0>,
  "pattern_flags": ["<specific pattern observations>"],
  "explanation": "<brief explanation>"
}}"""


# ---------------------------------------------------------------------------
# Stage 4: Deep AI Investigation (RED tier)
# ---------------------------------------------------------------------------

def build_investigation_prompt(
    doc_type: str,
    ela_score: float,
    metadata_score: float,
    seal_score: float,
    nlp_score: float,
    final_score: float,
    ela_flags: List[str],
    metadata_flags: List[str],
    seal_flags: List[str],
    nlp_flags: List[str],
    pattern_flags: List[str],
    ocr_text: str,
    extracted_fields: dict,
    registry_result: Optional[dict] = None,
) -> str:
    def fmt_flags(flags):
        return "\n".join(f"  - {f}" for f in flags) if flags else "  None"

    registry_section = ""
    if registry_result:
        registry_section = f"""
Registry Verification:
  Found: {registry_result.get('found', False)}
  Match: {registry_result.get('match', False)}
  Details: {registry_result.get('details', {})}"""

    return f"""You are a senior document forensics investigator analyzing a HIGH-RISK document.

DOCUMENT TYPE: {doc_type}
RISK SCORE: {final_score:.1f}/100 (RED tier — HIGH probability of fraud)

PIPELINE SCORES:
  ELA (pixel tampering):    {ela_score:.1f}/100
  Metadata forensics:       {metadata_score:.1f}/100
  Seal analysis:            {seal_score:.1f}/100
  NLP cross-document:       {nlp_score:.1f}/100

DETECTED ANOMALIES:

ELA Flags:
{fmt_flags(ela_flags)}

Metadata Flags:
{fmt_flags(metadata_flags)}

Seal Flags:
{fmt_flags(seal_flags)}

NLP/Cross-Document Flags:
{fmt_flags(nlp_flags)}

Pattern Detection:
{fmt_flags(pattern_flags)}
{registry_section}

EXTRACTED FIELDS:
{extracted_fields}

DOCUMENT TEXT SAMPLE:
\"\"\"
{ocr_text[:2000]}
\"\"\"

An ELA heatmap image showing pixel-level tampering evidence is also attached.

Provide a comprehensive forensic investigation summary:
{{
  "verdict": "<one of: GENUINE, LIKELY_FORGED, DEFINITELY_FORGED, INSUFFICIENT_EVIDENCE>",
  "confidence": <0.0 to 1.0>,
  "primary_tampering_method": "<description of likely tampering technique or null>",
  "key_evidence": ["<top 3-5 most compelling evidence points>"],
  "risk_explanation": "<2-3 sentence plain-English summary for a compliance officer>",
  "recommended_action": "<one of: APPROVE, MANUAL_REVIEW, REJECT, REQUEST_ORIGINAL>"
}}"""
