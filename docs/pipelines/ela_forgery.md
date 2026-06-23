# Pipeline: ELA Forgery Detection

The **ELA (Error Level Analysis) Forgery Detection** pipeline analyzes JPEG compression artifacts to detect pixel-level tampering in documents. It is optimized for bank documents, cheques, and financial statements.

---

## Technical Overview
When an image is edited and re-saved as JPEG, tampered regions undergo double compression, creating distinctive error patterns. ELA reveals these patterns by re-compressing the image and measuring pixel-wise differences.

### Core Analysis Features
1. **Multi-Quality ELA**: Sweeps JPEG qualities (75, 85, 95) and fuses the resulting error maps to suppress false positives from JPEG ringing artifacts.
2. **JPEG Ghost Detection**: Identifies compression history mismatches that reveal spliced or pasted regions.
3. **Document-Aware Preprocessing**: Optional CLAHE contrast normalization and Gaussian blur reduce text-edge noise, which commonly triggers false positives on text-heavy documents.

### Risk Scoring Components
The pipeline contributes to the overall risk score through seven sub-metrics:

| Component | What It Detects |
|-----------|-----------------|
| Spatial clustering | Localized error concentration |
| Local contrast | Sharp transitions in error magnitude |
| Global outliers | Extreme pixel differences |
| Uniformity | Error consistency (coefficient of variation) |
| JPEG ghost score | Compression history mismatch |
| Noise inconsistency | Anomalous sensor noise patterns |
| Grid mismatch | 8×8 JPEG grid boundary artifacts |

---

## How to Run ELA Forgery Detection
To analyze a document for pixel-level tampering:
```bash
# Run direct analysis — ELA subscore is included in the diagnostic card
python -m checkmate_cli analyze doc.pdf

# Open interactive shell and query the AI about tampering regions
python -m checkmate_cli
CheckMate >> /analyze doc.pdf
CheckMate [doc.pdf] >> are there any pixel tampering zones?
```

**Screenshot Space Placeholder:**
*(Insert ELA Heatmap and Anomaly Mask screenshot here)*
