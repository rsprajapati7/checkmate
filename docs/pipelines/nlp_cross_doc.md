# Pipeline: NLP Cross-Doc Scrutiny

The **NLP Cross-Document Scrutiny** pipeline executes semantic text validation, document format consistency checks, and QR-to-OCR cross-verification.

---

## Technical Overview
Even if a document is visually perfect, the information written within it must be logically consistent. The NLP pipeline parses the OCR and native text layers to extract entities and check them against strict grammatical and mathematical rules.

### 1. Entity Extraction
The system utilizes regular expressions and pattern extractors to locate:
- **Aadhaar Numbers**: Extracts 12-digit patterns.
- **PAN Numbers**: Extracts Indian Income Tax PAN codes (e.g. `ABCDE1234F`).
- **GSTINs**: Extracts GST identification numbers.
- **Financial Currencies**: Identifies currency formats and extracts decimal monetary amounts.

### 2. Consistency & Validation Rules
- **PAN/Aadhaar/GST Format Verification**: Validates formatting rules (such as PAN alphanumeric structure) and checks for uniqueness across multiple mentions.
- **Balance Sheet Arithmetic**: If the document is classified as a financial statement (e.g. balance sheet), it verifies that:
  $$\text{Total Assets} = \text{Total Liabilities} + \text{Total Equity}$$
- **Revenue vs GST Alignment**: Checks if the reported total revenue matches the expected GST turnover values.
- **QR code vs OCR Text Validation**: Safely decodes embedded QR payloads (JSON, URL, or dict-like strings) and checks if names, IDs, dates, or roll numbers mentioned in the QR code are present in the OCR text. If a PAN/Aadhaar number in the QR does not match the OCR text, it flags it as a high-severity critical anomaly.

---

## How to Run NLP Scrutiny
To review consistency checks:
```powershell
# Run direct analysis and check the NLP subscore in the diagnostic card
python -m checkmate_cli analyze doc.pdf

# Open interactive shell and query Gemma about the document's consistency
python -m checkmate_cli
CheckMate >> /analyze doc.pdf
CheckMate [doc.pdf] >> does the GSTIN match the client name?
```

**Screenshot Space Placeholder:**
*(Insert NLP Consistency Graph and QR Verification Mismatch screenshot here)*
