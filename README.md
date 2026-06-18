# CheckMate / Suraksha 2.0 — AI Document Forensic Toolkit

CheckMate is a professional, multi-layered document verification and forensic analysis suite. It combines deep learning models (YOLOv8), optical character recognition (EasyOCR/Tesseract), statistical image analysis (Error Level Analysis), and Large Language Models (Gemma-4-31b) to detect structural, visual, and semantic forgeries in high-stakes documents (such as bank statements, invoices, academic certificates, and identity cards).

---

## Architecture Overview

The system consists of three main components:
1. **Forensic Backend Core (FastAPI)**: An API server that hosts the analytical pipelines, runs YOLOv8 model inference for stamp detection, parses XMP schemas, checks logical entities, and interfaces with the LLM reasoning loop.
2. **Python Command-Line Interface (CheckMate CLI)**: A high-fidelity console tool built with **Typer** and **Rich** (featuring fallback terminal prompts via **prompt_toolkit**). It allows users to run complete forensic checks locally from their terminal.
3. **Web Application Dashboard (Upcoming)**: A modern, web-based tool is planned to provide a visual interface for uploading documents, interactive heatmap navigation, and managing historical reports.

---

## Forensic Pipelines

CheckMate's analysis is broken down into modular pipelines. Click on each pipeline to view a detailed explanation of its technical logic and how it works:

- [Document Ingestion](docs/pipelines/document_ingestion.md): normalizes documents, renders pages, and extracts native and OCR text.
- [Error Level Analysis (ELA) Forgery](docs/pipelines/ela_forgery.md): analyzes compression noise changes to isolate modified pixels.
- [Metadata Forensics](docs/pipelines/metadata_forensics.md): runs PDF dictionaries against a state machine of date and editing tool rules.
- [Seal & Signature Detection](docs/pipelines/seal_detection.md): YOLO-driven stamp extraction and boundary sharpness checks.
- [NLP Cross-Doc Scrutiny](docs/pipelines/nlp_cross_doc.md): validates Indian ID formatting, balance-sheet math, and QR-to-OCR alignments.
- [Score Fusion](docs/pipelines/score_fusion.md): combines all pipeline metrics into a unified threat tier (Green, Yellow, Red).

---

## Deployment & Production Hosting

CheckMate supports offline hosting on cloud environments. If you are deploying the backend core to a remote virtual machine (such as Oracle Cloud Infrastructure) with an offline LLM, see the detailed setup guide:

- [OCI VM Deployment & Offline LLM Setup](docs/pipelines/vm_deployment.md): Guides you through Docker compose, host-based Ollama bindings, and network/firewall configurations.

---

## Running CheckMate CLI Locally

If you want to run CheckMate locally, follow the steps below to set up the backend server and configure the CLI tool.

### Prerequisites
- **Python 3.10+**
- **CUDA Toolkit** (Optional; required for GPU acceleration of YOLOv8 and EasyOCR)
- **Tesseract OCR Binary** (Required for PDF character fallback processing)

---

### Step 1: Environment Setup
Clone the repository and set up a Python virtual environment:
```powershell
# Navigate to project root
cd checkmate

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install core packages
pip install -r requirements.txt
```

---

### Step 2: Configure Environment Variables
Create a `.env` file in the root directory by copying `.env.example` and filling in your values:
```ini
DATABASE_URL=sqlite+aiosqlite:///./checkmate.db
LLM_PROVIDER=ollama
LLM_MODEL=gemma:2b
OLLAMA_API_BASE=http://localhost:11434
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

### Step 3: Launch the Backend Server
Start the FastAPI backend server using Uvicorn:
```powershell
.\venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*(Leave this running in the background. The server listens on `http://localhost:8000`)*

---

### Step 4: Run the CLI Setup Wizard
In a new terminal window, activate the virtual environment and initialize the CLI configuration:
```powershell
# Set UTF-8 encoding (critical for Windows console boxes)
$env:PYTHONIOENCODING="utf-8"

# Launch interactive setup
python -m checkmate_cli setup
```
Provide the API URL (`http://localhost:8000`) and save your credentials.

**Screenshot Space Placeholder:**
*(Insert CLI Setup Wizard screenshot here)*

---

## CLI Usage Guide

CheckMate CLI supports both direct command execution and a full interactive REPL shell.

### 1. Direct Document Analysis
Directly scan a document and display the forensic table and AI summary:
```powershell
python -m checkmate_cli analyze <path_to_pdf_or_image>
```

**Screenshot Space Placeholder:**
*(Insert CLI Analyze Command Output table here)*

---

### 2. Interactive Shell (REPL)
Launch the interactive shell by running the command with no arguments:
```powershell
python -m checkmate_cli
```
This boots up system diagnostics, checks API health, and opens a `CheckMate >> ` session.

**Screenshot Space Placeholder:**
*(Insert Interactive Shell Startup banner here)*

#### Shell Slash Commands:
- `/analyze <path>` (or `/a`): Load and scan a document.
- `/report <output.html>` (or `/r`): Export the compiled report.
- `/reset` (or `/rt`): Clear chat memory and reset document selection.
- `/status` (or `/s`): Refresh backend server connection.
- `/clear` (or `/c`): Clear terminal screen.
- `/exit` (or `/q`): Exit the session.

#### Natural Language Routing (Gemma Assistant)
Any input typed in the shell that does *not* begin with `/` is routed to the Gemma assistant as a question. If a document is active (loaded), Gemma receives its full forensic report context:
```powershell
CheckMate [invoice.pdf] >> why is the risk score moderate?
```
Gemma will analyze the metadata and ELA anomalies and respond to your inquiry.

---

## Theme & Styling Guidelines
CheckMate CLI uses a custom-tailored theme built on the **Rich** styling engine to create a modern visual look:
- **Primary Gold (`#D4AF37`)**: Used for titles, spinners, and active command prompts.
- **Coral Warning (`#D1855C`)**: Highlights moderate risk tiers and warnings.
- **Sage Success (`#8DECB4`)**: Denotes healthy connections and verified-safe assets.
- **Crimson Alert (`#C0392B`)**: Indicates critical threat detections.
- **Slate Text (`#4A4A5A`)**: Used for descriptions, logs, and sub-labels.

---

## Future Roadmap: Web Application
While the CLI is built for developers and local forensic review, we are designing a web-based client that will include:
* drag-and-drop document upload.
* Interactive ELA heatmap overlay magnifier.
* Historical audit logs.
* Visual pipeline timelines.
