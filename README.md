<div align="center">

<img src="docs/assets/Banner.png" alt="CheckMate Banner" width="100%" />

### AI-Powered Document Forensics From Your Terminal

Detect forged bank statements, cloned seals, and tampered KYC documents using multi-pipeline forensic analysis, powered by computer vision and LLM reasoning.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?logo=opencv&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

> [!NOTE]
> **Offline-First**: All forensics, OCR, ELA, and LLM investigation run fully on your local machine. The entire system operates air-gapped — no document data ever leaves your environment.

---

## Demo

<video src="https://github.com/user-attachments/assets/c50f7bb2-518a-4f75-af0e-dba2b509240c" width="100%" controls></video>

<!-- Presentation link (uncomment and update when available)
📊 [View the Presentation Deck](link-to-presentation)
-->

---

## Problem

India's financial system processes millions of documents daily — bank statements, tax returns, KYC records, land registrations. Sophisticated forgeries involving manipulated figures, cloned official seals, and doctored metadata slip past manual review. The ₹22,842 crore ABG Shipyard fraud went undetected for 14 years because forged balance sheets fooled 28 banks.

Existing tools check **one thing** — OCR text *or* metadata *or* pixel analysis. No single tool cross-references all evidence to catch multi-layered tampering.

---

## Solution

CheckMate runs **four forensic pipelines in parallel**, fuses their findings into a calibrated risk score, and uses an LLM to explain exactly *why* a document is suspicious — all from your terminal.

Upload a document → the system ingests, analyzes, cross-references, and scores it in seconds → you get a verdict with full forensic evidence.

---

## Features

### Forensic Analysis
- **Error Level Analysis (ELA)** — Multi-scale JPEG recompression analysis with CLAHE preprocessing and GHOST compression detection to reveal pixel-level tampering
- **Metadata Forensics** — 8 anomaly rules checking date conflicts, producer mismatches, design software footprints, and XMP/PDF dictionary drift
- **Seal & Stamp Detection** — YOLOv8 localization with heuristic fallback (color HSV + Hough circles), per-crop ELA scoring, and Laplacian edge sharpness analysis
- **NLP Cross-Document Scrutiny** — Regex-based entity extraction (PAN, Aadhaar, GSTIN), balance-sheet arithmetic validation, and QR-to-OCR cross-verification

### AI Intelligence
- **LLM-as-Investigator** — Gemma receives full forensic context (scores, flags, ELA heatmaps) and reasons about *why* a document is suspicious
- **Conversational Forensics** — Ask follow-up questions in natural language; the AI responds with contextual explanations against the active document
- **Dual-Provider Support** — Google AI Studio (Gemma 4) for cloud, Ollama for fully offline operation

### India-Specific
- **Regulatory Validation** — PAN (`ABCDE1234F`), Aadhaar (12-digit), GSTIN (15-char) format enforcement
- **UGC University Recognition** — Cross-checks institutions against a registry of recognized universities
- **Financial Document Guards** — Balance sheet equation checks, GST turnover alignment, ITR date validation

### CLI Experience
- **Interactive REPL Shell** — Slash commands, streaming AI responses, animated pipeline progress
- **Visual Dashboards** — ELA heatmap and seal detection dashboards generated as diagnostic images
- **Rich-Themed Output** — Custom color palette (Gold/Coral/Sage/Crimson) built on the Rich styling engine
- **PDF/HTML Reports** — Jinja2-templated forensic reports with embedded heatmaps and scoring breakdowns

---

## Architecture

```
 Upload (PDF/Image)
        │
        ▼
 ┌─────────────┐
 │  Ingestion  │  PyMuPDF (300 DPI) → OCR (Tesseract) → QR Decode (pyzbar)
 └──────┬──────┘
        │
        ▼
 ┌───────────────────────────────────────────────┐
 │         PARALLEL PIPELINES (asyncio.gather)   │
 │                                               │
 │  ┌────────┐  ┌──────────┐  ┌──────┐  ┌─────┐  │
 │  │  ELA   │  │ Metadata │  │ Seal │  │ NLP │  │
 │  └───┬────┘  └────┬─────┘  └──┬───┘  └──┬──┘  │
 └──────┼────────────┼───────────┼─────────┼─────┘
        └────────────┴───────────┴─────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │      Fusion Engine     │  Weighted scoring (scanned vs digital profiles)
              │   GREEN / AMBER / RED  │
              └─────────┬──────────────┘
                        │
                  ┌─────┴──────┐
                  │  RED only  │
                  ▼            │
          ┌─────────────────┐  │
          │ AI Investigator │  │
          │ (Gemma / Ollama)│  │
          └──────┬──────────┘  │
                 └─────────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Report (PDF/HTML) │
              └────────────────────┘
```

**Pipeline deep-dives:**
[Document Ingestion](docs/pipelines/document_ingestion.md) · [ELA Forgery](docs/pipelines/ela_forgery.md) · [Metadata Forensics](docs/pipelines/metadata_forensics.md) · [Seal Detection](docs/pipelines/seal_detection.md) · [NLP Cross-Doc](docs/pipelines/nlp_cross_doc.md) · [Score Fusion](docs/pipelines/score_fusion.md)

---

## Screenshots

**CLI Dashboard:**

<img width="100%" alt="CLI Dashboard" src="https://github.com/user-attachments/assets/10d7587f-2141-4d3b-b826-58de663a14e2" />

**ELA Dashboard:**

<img width="100%" alt="ELA Dashboard" src="docs/assets/Rajat_page_1_ela_dashboard.png" />

**Seal & Stamp Detection:**

<img width="100%" alt="Seal Detection Dashboard" src="docs/assets/Rajat_page_1_seal_dashboard.png" />

---

## Installation

For the full setup guide (OS-specific dependencies, GPU/CUDA configuration, Ollama LLM setup, and troubleshooting), see **[docs/setup.md](docs/setup.md)**.

### Quick Start

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
cd checkmate
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set TESSERACT_CMD to your Tesseract path
```
</details>

<details>
<summary><strong>macOS (Homebrew)</strong></summary>

```bash
cd checkmate
brew install tesseract
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
cd checkmate
sudo apt-get install tesseract-ocr libtesseract-dev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
</details>

---

## Usage

### 1. Start the Backend
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 2. Configure the CLI (first time only)
```bash
python -m checkmate_cli setup
```

### 3. Analyze a Document
```bash
python -m checkmate_cli analyze invoice.pdf
```

### 4. Interactive Shell
```bash
python -m checkmate_cli
```

**Example session:**
```
CheckMate >> /analyze suspicious_bank_statement.pdf

  ┌─────────────────────────────────────────┐
  │  RISK SCORE: 73/100      Tier: RED      │
  ├─────────────────────────────────────────┤
  │  ELA Forgery:            68/100         │
  │  Metadata:               81/100         │
  │  Seal Detection:         42/100         │
  │  NLP Cross-Doc:          55/100         │
  └─────────────────────────────────────────┘

CheckMate [suspicious_bank_statement.pdf] >> why is the metadata score so high?

  The metadata score is elevated because of two critical anomalies:
  1. The PDF's CreationDate (2023-01-15) is later than its ModDate
     (2022-11-03), which is physically impossible without tampering.
  2. The Producer field indicates "Scanner" but the document contains
     Adobe Illustrator layer markers, suggesting post-scan editing.
```

**Slash commands:**

| Command | Shortcut | Description |
|---------|----------|-------------|
| `/analyze <path>` | `/a` | Scan a document |
| `/dashboard <ela\|seal> [page]` | `/d` | Open visual diagnostic dashboard |
| `/report <output.html>` | `/r` | Export forensic report |
| `/status` | `/s` | Check backend connection |
| `/reset` | `/rt` | Clear chat history |
| `/exit` | `/q` | Exit |

### Remote Deployment

For deploying on a VM with an offline LLM, see the [OCI VM Deployment Guide](docs/deployment/vm_deployment.md).

---

## License

This project is licensed under the [MIT License](LICENSE).
