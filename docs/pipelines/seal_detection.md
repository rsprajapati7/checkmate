# Pipeline: Seal & Signature Detection

The **Seal & Signature Detection** pipeline identifies official stamps, seals, and signatures, and determines if they are authentic impressions or digital overlays pasted on top of a scanned document.

---

## Technical Overview
Physical documents are often scanned after being stamped. If a stamp is digitally copied and pasted onto a scanned document, it leaves forensic footprints (such as artificial sharpness borders or compression discrepancies).

The pipeline uses two core algorithms for stamp localization, followed by edge analysis:

### 1. Localization Engine
* **YOLOv8 Object Detection**: A customized YOLOv8 convolutional neural network (`models/yolov8/seal_detector.pt`) locates stamps, seals, and signatures. It automatically runs on the **GPU (CUDA)** if available, otherwise defaulting to the CPU.
* **Color Heuristic & Contour Detection (Fallback)**: If YOLOv8 is unavailable, the pipeline falls back to an OpenCV color-space binarization. It searches for typical ink colors (Red, Blue, Purple, Magenta) and uses morphological closing + contour aspect ratio checks.
* **Hough Circle Transform (Fallback)**: If color extraction fails, the engine applies a Hough Circle Transform to isolate circular stamp outlines.

### 2. Forensic Edge Analysis
Once a seal region is cropped, the engine checks:
1. **Edge Sharpness (Laplacian Variance)**: Paste-ups are digitally crisp, whereas authentic scanned stamps have blurry borders due to scan-resolution limits. A Laplacian variance score `>500` indicates artificial sharpness.
2. **Local ELA Mismatch**: Evaluates the recompression error specifically within the cropped seal bounding box. Pasted stamps exhibit highly elevated ELA averages compared to the surrounding page canvas.

---

## How to Run Seal Detection
To analyze seals in a document:
```bash
# Run direct analysis and review detected seals summary
python -m checkmate_cli analyze doc.pdf

# Generate and open the visual seal dashboard
python -m checkmate_cli
CheckMate >> /analyze doc.pdf
CheckMate [doc.pdf] >> /dashboard seal
```

---

## Model Availability Note

The YOLOv8 seal detection model (`seal_detector.pt`) is **not included** in this repository. Training a custom seal detector requires a labeled dataset of Indian government and institutional seals, which is not publicly available at this time.

**What this means in practice:** When the model file is absent, the pipeline automatically and silently falls back to the heuristic detection chain (color binarization → contour analysis → Hough circles). This fallback produces usable results for common stamp types but with lower precision than a trained YOLO model.

To use a custom-trained model, place the `.pt` file at the path specified in your `.env` (`YOLO_MODEL_PATH`, default: `models/yolov8/seal_detector.pt`).
