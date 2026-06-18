# Pipeline: Error Level Analysis (ELA) Forgery Detection

The **Error Level Analysis (ELA)** pipeline is a core forensic technique that detects digital tampering by highlighting inconsistencies in JPEG compression levels.

---

## Technical Overview
When a JPEG image is saved, the entire canvas is compressed uniformly at an 8x8 block level. If a portion of that image is later edited, spliced, or digitally modified, and the resulting file is saved as a new JPEG, the tampered region undergoes double-compression, causing its error level to differ from the authentic parts.

```
Original Image (JPEG Q=90)
       ↓
[ Edit / Splicing ]
       ↓
Resaved Image (JPEG Q=90) -> Edited parts double-compressed, authentic parts triple-compressed.
```

### Steps in the ELA Engine
1. **Luminance Normalization**: Converts RGB input to YCrCb space, focusing primarily on the Y (luminance) channel where compression errors are most prominent.
2. **Multi-Quality Recompression**:
   * ELA re-saves the image at multiple target JPEG qualities (e.g. 75, 85, 95).
   * It computes the pixel-wise absolute difference between the original image and the re-compressed variants.
3. **Ghost Analysis**: Compares error rates across quality ranges to isolate the image's original compression history (revealing the "JPEG Ghost" mismatch ratio).
4. **Scoring Features**:
   * **Spatial Clustering**: Detects local concentrations of high error values.
   * **CV (Coefficient of Variation)**: Computes overall image error uniformity.
   * **Grid Alignment**: Identifies block boundary offsets caused by non-aligned cropping.

---

## ELA Diagnostic Heatmap
The CLI outputs a visual diagnostic representation. In a standard ELA heatmap overlay:
- **Dark/Uniform Grayscale**: Indicates authentic, unedited regions (compression errors have stabilized).
- **Bright/Color-Clustered Spots**: Indicates edited text, spliced stamps, or metadata injections (high compression delta).

---

## How to Run ELA Forensics
You can inspect the ELA metrics directly via the CLI:
```powershell
# Scan document and view ELA subscore in CLI
python -m checkmate_cli analyze doc.pdf

# Open interactive shell to inspect visual ELA dashboards
python -m checkmate_cli
CheckMate >> /analyze doc.pdf
CheckMate [doc.pdf] >> /dashboard ela
```
**Screenshot Space Placeholder:**
*(Insert ELA Heatmap and Dashboard output screenshot here)*
