# Pipeline: Metadata Forensics

The **Metadata Forensics** pipeline analyzes the hidden structure and system dictionary logs embedded inside PDF and image headers to trace the history and authenticity of the document.

---

## Technical Overview
Tampered documents often look pristine visually, but their internal structure and metadata tags tell a different story. The CheckMate metadata engine extracts key-value headers and executes a state-machine of anomaly-detection rules.

### Core Anomaly Detection Rules
The system evaluates the following rules to assign a risk score:
1. **Creation Date Mismatch**: Flagged if `CreationDate` is chronologically later than the `ModDate` (indicative of manual metadata rewriting).
2. **Scanner & Producer Mismatch**: Conflicting headers (e.g., the `Producer` field claims a "Ricoh Office Scanner" but the `Creator` field lists "Adobe Photoshop" or "Illustrator").
3. **Design Software Origin**: Checks if the file was created or edited using graphic editing suites like **Canva, Photoshop, Figma, GIMP, InDesign, or Sketch**. Official financial documents (bank statements, tax certificates) should not originate from design suites.
4. **Incremental Save Anomaly**: Counts the number of update tables in the PDF body. A high count (e.g. >3) indicates a document that has been edited and saved repeatedly.
5. **XMP vs PDF Dict Mismatch**: Cross-checks metadata dates stored in the modern XMP schema against dates stored in the legacy PDF info dictionary. A difference greater than 24 hours suggests tampering.
6. **Future Dates**: Flags dates that exist in the future relative to the host system clock.

---

## Technical Indicators
The pipeline normalizes the triggered rules to output a score from `0` to `100`. 
- A high score indicates a high probability of metadata spoofing or editing tool footprints.

---

## How to Run Metadata Forensics
To review the metadata flags:
```powershell
# Analyze document directly
python -m checkmate_cli analyze doc.pdf

# Run shell REPL to inspect raw metadata JSON
python -m checkmate_cli
CheckMate >> /analyze doc.pdf
CheckMate [doc.pdf] >> /view metadata
```

**Screenshot Space Placeholder:**
*(Insert Metadata Diagnostic Table and Rule Flags screenshot here)*
