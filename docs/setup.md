# CheckMate — Installation & Setup Guide

This guide provides step-by-step instructions to configure and run the CheckMate document forensics toolkit. 

> [!NOTE]
> **Local-First & Offline Priority**: CheckMate is engineered to run fully offline. All document forensics, OCR extraction, Error Level Analysis (ELA), and LLM reasoning run locally on your hardware. No document data is sent to external clouds or third-party APIs unless explicitly configured.

---

## 1. Prerequisites

Before installing, ensure your system meets the requirements:

### Required Dependencies
* **Python 3.10 or 3.11** (Verify with `python --version`)
* **Tesseract OCR Engine**: Required for character recognition fallbacks on PDF images and scans.
* **Ollama (Optional)**: Required for running local LLMs offline.

### OS-Specific Tesseract Installation

#### Windows
1. Download the Tesseract installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install it to a directory of your choice (e.g., `C:\Program Files\Tesseract-OCR`).
3. Note the path to `tesseract.exe` (you will need to add this to your `.env` file).

#### Ubuntu / Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr libtesseract-dev
```

#### macOS (via Homebrew)
```bash
brew install tesseract
```

---

## 2. Hardware Recommendations (CPU vs GPU)

CheckMate utilizes heavy deep learning models (YOLOv8 for seal detection and EasyOCR/PyTorch).

* **CPU Execution**: Fully supported. Good for local testing or light volumes.
* **GPU Execution (NVIDIA)**: Highly recommended for professional or production environments. Enabling CUDA significantly reduces processing latency for ELA and YOLOv8 pipeline steps.

To enable GPU acceleration:
1. Ensure you have an NVIDIA GPU.
2. Install the appropriate **CUDA Toolkit** (e.g., v11.8 or v12.1) and matching PyTorch installation.

---

## 3. Step-by-Step Setup

### Step 3.1: Clone and Set Up Virtual Environment

Open your terminal, navigate to the project directory, and initialize a virtual environment:

```bash
# Navigate to the project root
cd checkmate

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (CMD):
.\venv\Scripts\activate.bat
```

### Step 3.2: Install Dependencies

With the virtual environment active, install the Python package requirements:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

1. Copy the template `.env.example` file to create your own configuration file:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file in an editor and configure the following parameters:

| Variable | Description | Recommended/Default Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLite database path for local audits. | `sqlite+aiosqlite:///./checkmate.db` |
| `LLM_PROVIDER` | Choose `ollama` for local offline, or `google` for Google AI Studio. | `ollama` |
| `LLM_MODEL` | The LLM model tag. | `gemma:2b` |
| `OLLAMA_API_BASE` | Local port URL where Ollama is running. | `http://localhost:11434` |
| `TESSERACT_CMD` | Full path to the Tesseract executable (critical on Windows). | `C:\Program Files\Tesseract-OCR\tesseract.exe` |

---

## 5. Local LLM Setup (Ollama)

To run the AI investigation and natural language report generation offline:

1. Download and install [Ollama](https://ollama.com/).
2. Start the Ollama background service.
3. Open a terminal and pull the lightweight model configured in your `.env` file:
   ```bash
   ollama pull gemma:2b
   ```

---

## 6. Running the Services

CheckMate operates via a FastAPI backend server and a conversational CLI frontend.

### Step 6.1: Start the Backend Orchestrator
Launch the Uvicorn server to run the analysis pipelines:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*(Keep this terminal running. The server listens at `http://localhost:8000`)*

### Step 6.2: Setup the CLI Profile
In a new terminal window (with the virtual environment active), run the CLI setup wizard to configure authentication credentials:
```bash
python -m checkmate_cli setup
```

---

## 7. Verifying the Setup

You can verify that everything is working by running a direct document scan:

```bash
python -m checkmate_cli analyze <path_to_pdf_or_image>
```

Or start the interactive REPL shell:
```bash
python -m checkmate_cli
```
On startup, it will run system diagnostics and display:
```text
[ OK ] System Status: CheckMate Core Online
[ OK ] Tesseract OCR Connection: Active
[ OK ] Local LLM Model (gemma:2b): Connected
```

---

## 8. Troubleshooting Common Issues

### 1. `TesseractNotFoundError`
* **Cause**: Python cannot locate the Tesseract executable.
* **Solution**: Ensure the `TESSERACT_CMD` path in your `.env` file points to the actual binary file (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe` on Windows) and contains no trailing quotes.

### 2. Ollama connection refused
* **Cause**: Ollama is not running, or is running on a different port.
* **Solution**: Launch the Ollama app or run `ollama serve` in a terminal. Verify that `OLLAMA_API_BASE` matches your Ollama port.

### 3. GPU is not being used
* **Cause**: PyTorch is defaulting to CPU.
* **Solution**: Verify CUDA installation in Python:
  ```python
  import torch
  print(torch.cuda.is_available()) # Should return True
  ```
  If it returns `False`, reinstall PyTorch with CUDA enabled: `pip install torch --index-url https://download.pytorch.org/whl/cu118`.
