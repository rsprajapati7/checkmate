# Pipeline: Score Fusion

The **Score Fusion** engine is the final stage of the CheckMate forensic check. It integrates the outputs of all individual pipelines (ELA, Metadata, Seal, and NLP) into a unified risk rating.

---

## Technical Overview
Different documents require different diagnostic weights. For instance, a digital PDF has no scan characteristics, so ELA and Seal detection are weighted differently than on physical scans.

### Mathematical Integration
The final integrated score (from `0` to `100`) is calculated as a weighted average of individual scores:

$$\text{Final Score} = (w_{\text{ELA}} \times S_{\text{ELA}}) + (w_{\text{Metadata}} \times S_{\text{Metadata}}) + (w_{\text{Seal}} \times S_{\text{Seal}}) + (w_{\text{NLP}} \times S_{\text{NLP}})$$

#### Default Weights (Configurable in `.env`)
- **Error Level Analysis ($w_{\text{ELA}}$)**: `0.35` (35%)
- **Metadata Forensics ($w_{\text{Metadata}}$)**: `0.25` (25%)
- **Seal & Signature Detection ($w_{\text{Seal}}$)**: `0.25` (25%)
- **NLP Cross-Doc Scrutiny ($w_{\text{NLP}}$)**: `0.15` (15%)

---

## Risk Tier Classification
The final score determines the document's risk category:

| Score Range | Risk Tier | Description | Recommended Action |
|-------------|-----------|-------------|---------------------|
| **0.0 – 29.9** | **GREEN (Verified Safe)** | Authentic; minimal or no anomalies detected. | Safe to process automatically. |
| **30.0 – 59.9** | **AMBER (Caution)** | Minor anomalies or tool indicators detected (e.g. Canva footprint). | Queue for secondary review. |
| **60.0 – 100.0** | **RED (Critical Alert)** | Splicing, date mismatch, or signature tampering detected. | Reject document or flag for investigator. |

---

## How to Check Scores
The threat index and category tier are prominent on the main diagnostic table:
```powershell
python -m checkmate_cli analyze doc.pdf
```
**Screenshot Space Placeholder:**
*(Insert Score Fusion Risk Card screenshot here)*
