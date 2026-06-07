# 🏗️ CheckMate — Hackathon Build Plan

---

## 👥 Team Split (Recommended)

| Person | Role |
|--------|------|
| Dev 1 | Backend + ELA Pipeline |
| Dev 2 | YOLOv8 Seal + Metadata Pipeline |
| Dev 3 | NLP + Fusion Engine |
| Dev 4 | Frontend (React UI + Heatmap) |

> Solo or 2-person team? Do Backend first, Frontend last.

---

## 📦 Phase 0 — Setup (2–3 hours)

- [ ] Create GitHub repo with `/backend` and `/frontend` folders
- [ ] Backend: `pip install fastapi uvicorn pymupdf pillow opencv-python pytesseract exiftool spacy reportlab ultralytics`
- [ ] Frontend: `npm create vite@latest` → React + Tailwind CSS
- [ ] Test a basic FastAPI `/health` endpoint returns `{"status": "ok"}`
- [ ] Test React app runs on localhost

---

## 🔧 Phase 1 — Backend Core (Day 1)

### 1.1 Ingestion Layer
**Goal:** Accept a PDF or image upload, convert it to a workable format.

```
POST /analyze
  → Save file
  → If PDF: convert pages to images (PyMuPDF)
  → If image: use directly
  → Run OCR (Tesseract) to extract text
  → Extract metadata (ExifTool)
  → Pass to 4 pipelines
```

Files to create:
- `backend/main.py` — FastAPI app + `/analyze` route
- `backend/ingestion.py` — PDF→image, OCR, metadata extraction

---

### 1.2 ELA Pipeline (`pipelines/ela.py`)
**Difficulty:** ⭐⭐ Easy-Medium

```python
# Steps:
# 1. Open image with Pillow
# 2. Re-save at 95% JPEG quality
# 3. Compute pixel difference (ImageChops.difference)
# 4. Normalize mean intensity to 0-100 score
# 5. Return score + ELA heatmap image
```

✅ Output: `{ "score": 45, "heatmap": "base64_image" }`

---

### 1.3 Metadata Pipeline (`pipelines/metadata.py`)
**Difficulty:** ⭐ Easy

Checks to implement:
- [ ] `CreationDate > ModDate` → flag (score +40)
- [ ] PDF Producer says "Scanner" but has Illustrator/Photoshop tags → flag (score +50)
- [ ] Missing metadata fields entirely → flag (score +20)
- [ ] Author field blank on official document → mild flag (score +10)

✅ Output: `{ "score": 60, "flags": ["Date anomaly", "Producer mismatch"] }`

---

## 🤖 Phase 2 — ML + NLP Pipelines (Day 2)

### 2.1 Seal Detection (`pipelines/seal.py`)
**Difficulty:** ⭐⭐⭐ Medium

```
Steps:
1. Run YOLOv8 on document image → find seal/stamp regions
2. Crop each detected seal
3. Run ELA on the cropped seal
4. Check edge sharpness (unnaturally sharp = pasted)
5. Score based on findings
```

> 💡 Tip: Use `ultralytics` YOLOv8 pretrained on common objects first.  
> Train a custom seal model if time permits using labeled stamp images.

✅ Output: `{ "score": 70, "seals_found": 2, "suspicious": 1 }`

---

### 2.2 Cross-Document NLP (`pipelines/crossdoc.py`)
**Difficulty:** ⭐⭐⭐ Medium

```
Steps:
1. Extract text from all uploaded docs (Tesseract/PyMuPDF)
2. Use spaCy / regex to find:
   - PAN number (format: ABCDE1234F)
   - GST number
   - Revenue / Net Profit figures
   - Assets, Liabilities, Equity values
   - Document dates
3. Cross-check rules:
   - Same PAN across all docs? ✅
   - Assets = Liabilities + Equity? ✅ (allow ±5% tolerance)
   - Revenue in P&L matches GST turnover? ✅ (allow ±20%)
   - ITR filing date after financial year end? ✅
4. Each failed check adds to score
```

✅ Output: `{ "score": 55, "flags": ["Revenue mismatch", "PAN inconsistency"] }`

---

### 2.3 Fusion Engine (`fusion.py`)
**Difficulty:** ⭐ Easy

```python
def calculate_final_score(ela, metadata, seal, nlp):
    score = (ela*0.30) + (metadata*0.25) + (seal*0.25) + (nlp*0.20)
    if score < 30:   tier = "GREEN"
    elif score < 60: tier = "AMBER"
    else:            tier = "RED"
    return round(score, 2), tier
```

---

## 🎨 Phase 3 — Frontend (Day 2–3)

### Pages to Build

**Page 1: Upload Screen**
- Drag & drop multiple file upload
- File type validation (PDF, JPG, PNG)
- "Analyze" button → calls `/analyze`
- Loading spinner while processing

**Page 2: Results Dashboard**
- Big risk score gauge (0–100) in GREEN/AMBER/RED
- 4 pipeline score cards
- Heatmap overlay on document image (Canvas API)
- List of flags/anomalies detected
- "Download Report" button

### Components
```
src/
├── components/
│   ├── Upload.jsx         ← drag & drop
│   ├── ScoreGauge.jsx     ← big risk meter
│   ├── PipelineCard.jsx   ← score per pipeline
│   ├── HeatmapViewer.jsx  ← Canvas overlay
│   └── FlagList.jsx       ← anomaly list
├── App.jsx
└── api.js                 ← axios calls to backend
```

---

## 📋 Phase 4 — Report Generation (Day 3)

File: `backend/report.py`

PDF Report should contain:
- [ ] Document name + timestamp
- [ ] Final risk score + tier
- [ ] Per-pipeline scores table
- [ ] List of all flags with severity
- [ ] ELA heatmap image embedded
- [ ] Conclusion text

Use **ReportLab** for generating the PDF.

---

## 🔁 Full API Flow

```
User uploads files
      ↓
POST /analyze (FastAPI)
      ↓
ingestion.py → extract text, images, metadata
      ↓
asyncio.gather() runs all 4 pipelines in parallel
      ↓
fusion.py → combines scores
      ↓
report.py → generates PDF
      ↓
Response: { score, tier, flags, heatmap, report_url }
      ↓
Frontend displays results
```

---

## ✅ Day-by-Day Timeline

| Day | Goal |
|-----|------|
| Day 1 AM | Setup + Ingestion Layer + ELA pipeline |
| Day 1 PM | Metadata pipeline + basic FastAPI working end-to-end |
| Day 2 AM | Seal detection (YOLOv8) + NLP pipeline |
| Day 2 PM | Fusion engine + Frontend upload page |
| Day 3 AM | Frontend results dashboard + heatmap |
| Day 3 PM | PDF report + bug fixes + demo prep |

---

## 🧪 Testing Your Build

Create these test cases:
1. **Clean document** → should score GREEN (<30)
2. **Edited in Photoshop** → ELA should catch it, RED
3. **Copy-pasted seal** → Seal pipeline should flag it
4. **Two docs with different PAN** → NLP should catch mismatch
5. **PDF with wrong metadata dates** → Metadata pipeline flags it

> 💡 Use real-looking fake documents for the demo. Judges love visual proof.

---

## ⚠️ Common Pitfalls

- Tesseract needs to be installed separately (`sudo apt install tesseract-ocr`)
- ExifTool needs system install too (`sudo apt install libimage-exiftool-perl`)
- YOLOv8 first run downloads model weights — do this before demo day
- CORS must be enabled in FastAPI for frontend to call backend
- Keep ELA heatmap as base64 in JSON response to avoid file serving complexity

---

## 🏁 Minimum Viable Demo (if short on time)

Just get these 3 things working:
1. ✅ ELA pipeline (most visually impressive)
2. ✅ Metadata pipeline (easy + reliable)
3. ✅ Frontend showing score + heatmap

NLP and Seal detection can be shown as "in progress" or mocked scores.

---

> 🎯 **Goal:** A working demo where you upload a real forged document and the system catches it live. That's what wins hackathons.
