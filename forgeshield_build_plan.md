# ForgeShield — Final Build Plan

**Team**: 3 students (basic coding experience)  
**Timeline**: May 19–24, 2026 (5 days)  
**Theme**: Real-Time Anomaly Detection  
**Frontend**: React + Vite + Tailwind + shadcn/ui  
**LLM**: Local Ollama (Llama 3.2) for cross-doc analysis

---

## Team Role Assignment

| Person | Primary | Also Helps With |
|---|---|---|
| **A** | Backend (FastAPI, ingestion, metadata, orchestration) | Docker, scoring fusion |
| **B** | ML pipelines (ELA, YOLOv8 seal detection, heatmaps) | Cross-doc LLM wrapper (Ollama) |
| **C** | Frontend (React + Vite + Tailwind + shadcn/ui) | Demo documents, slide deck |

---

## Architecture Overview

```
Upload PDF/Image
       │
       ▼
  ┌─────────────┐
  │  FastAPI     │
  │  Ingestion   │
  │  (PyMuPDF)   │
  └──────┬───────┘
         │
         ▼
  ┌─────────────────────────────────────┐
  │   PARALLEL PIPELINES (asyncio)      │
  │                                     │
  │  ┌──────────┐  ┌───────────────┐   │
  │  │   ELA    │  │   Metadata    │   │
  │  │ (Pillow) │  │  (Rule-based) │   │
  │  └────┬─────┘  └──────┬────────┘   │
  │       │               │            │
  │  ┌────▼─────┐  ┌──────▼────────┐  │
  │  │   Seal   │  │  Cross-doc    │  │
  │  │ YOLOv8n  │  │ Ollama Llama  │  │
  │  │  + ELA   │  │    3.2        │  │
  │  └────┬─────┘  └──────┬────────┘  │
  └───────┼───────────────┼────────────┘
          │               │
          ▼               ▼
  ┌──────────────────────────────┐
  │     SCORING & FUSION         │
  │  Weighted risk score (0-100) │
  │  Risk tier: Green/Amber/Red  │
  └──────────────┬───────────────┘
                 │
                 ▼
  ┌──────────────────────────────┐
  │    FRONTEND (React+Tailwind) │
  │  Heatmap overlay, bounding   │
  │  boxes, contradiction table  │
  │  Risk gauge, demo mode       │
  └──────────────────────────────┘
```

---

## Day-by-Day Execution

### Day 1 — May 19 (Foundation)

| Person | Tasks |
|---|---|
| **A** | FastAPI project structure, PDF→page images (PyMuPDF), file upload endpoint returning document_id |
| **B** | Install ultralytics, Pillow, NumPy, OpenCV. Build basic ELA function (compress → diff → score → heatmap) |
| **C** | Bootstrap Vite + React + Tailwind + shadcn/ui. Build drag-and-drop file upload component. Set up Axios for API calls |

**Checkpoint**: Upload a PDF → backend extracts pages → returns JSON skeleton → frontend shows upload success

---

### Day 2 — May 20 (Core Pipelines)

| Person | Tasks |
|---|---|
| **A** | Metadata pipeline (6 checks: CreationDate>ModDate, producer mismatch, author anomalies, etc.). Pipeline orchestrator with asyncio |
| **B** | YOLOv8n pre-trained inference for seal detection (no fine-tuning). Crop detected regions → run ELA on seal area. Generate bounding box coordinates |
| **C** | Build result cards: ELA heatmap display + score gauge, metadata anomaly list with severity icons, overall risk score badge |

**Checkpoint**: Upload tampered doc → ELA heatmap + metadata anomaly list visible in frontend

---

### Day 3 — May 21 (Seal + Cross-doc + Integration)

| Person | Tasks |
|---|---|
| **A** | Wire all pipelines into `/analyze` endpoint. Implement scoring fusion (ELA 30%, metadata 25%, seal 25%, cross-doc 20%). Serve heatmap images via `/static` |
| **B** | Install Ollama, pull Llama 3.2. Build cross-doc module: extract text with PyMuPDF/pdfplumber → send to Ollama → parse structured JSON response for entities + inconsistencies |
| **C** | Seal detection card (document viewer with Canvas bounding box overlay). Cross-doc contradiction table. Multi-document upload mode |

**Checkpoint**: Full end-to-end — upload doc set → all 4 pipelines run → complete results in frontend

---

### Day 4 — May 22 (Polish + Demo Prep)

| Person | Tasks |
|---|---|
| **A** | Error handling (corrupt files, password-protected PDFs, unsupported formats). File validation. Docker + Docker Compose setup |
| **B** | Tune ELA thresholds on 5 test docs. Test YOLOv8 inference speed. Calibrate scoring weights. Prepare 5 demo documents (2 authentic, 3 tampered) |
| **C** | "Demo Mode" button with pre-loaded sample docs. Loading states, error states, mobile responsiveness. Final UI polish |

**Checkpoint**: Docker runs cleanly. Demo documents load correctly. Everything is demo-ready

---

### Day 5 — May 23 (Rehearsal + Submission)

| Person | Tasks |
|---|---|
| **All** | Full end-to-end test on presentation machine. Time the demo (target: 90s). Record backup screen recording. Push final code to GitHub. Write README. Prepare submission form |

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python 3.11 + FastAPI | API server, pipeline orchestration |
| Document | PyMuPDF, pdfplumber | PDF → images, text extraction |
| ELA | Pillow, NumPy, OpenCV | Error Level Analysis |
| Seal Detection | YOLOv8n (ultralytics) | Pre-trained object detection |
| LLM | Ollama + Llama 3.2 | Cross-doc entity extraction + inconsistency detection |
| Async | asyncio | Parallel pipeline execution |
| Frontend | React + Vite + Tailwind + shadcn/ui | UI framework |
| Visualization | Canvas API, react-pdf-viewer | Heatmap, bounding boxes |
| Container | Docker + Docker Compose | One-command deployment |

---

## Simplified Scope (for 3 beginners)

- **ELA**: Pillow-based, works on single images → multi-page PDF if time permits
- **Seal Detection**: YOLOv8n pre-trained on COCO (no fine-tuning). Detects circular objects → runs ELA on cropped region
- **Cross-doc NLP**: Extract text → Ollama (Llama 3.2) → structured JSON response
- **No PDF report generation** (stretch goal)
- **Frontend**: shadcn/ui pre-built components for speed

---

## Demo Script (90 seconds)

```
0:00–0:20  "In the ABG Shipyard fraud, forged balance sheets fooled 28 banks 
            for 14 years. The inconsistencies were there — no one had a tool 
            to find them automatically."

0:20–0:45  "Bank underwriters manually review documents under time pressure. 
            ForgeShield automates forensic analysis using 4 parallel pipelines."

0:45–1:00  "Upload a tampered land record → watch ELA highlight the edited region. 
            Upload a document with cloned seal → watch seal detection catch it."

1:00–2:30  Live demo — upload 3 pre-prepared documents, show results

2:30–3:00  "This reduces review time from 45 minutes to 30 seconds. 
            Roadmap: DigiLocker integration, RBI reporting."
```

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Ollama too slow on CPU | Pre-extract entities; cache results; show cached demo first |
| YOLOv8 detection inaccurate | Fallback: contour detection for circular regions |
| React frontend takes too long | Use shadcn/ui templates, keep design minimal |
| Demo breaks live | Record backup 90-second screen recording |
| Team member unavailable | Each person documents their module; modular code |
