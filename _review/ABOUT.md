# \_review/ — Files Pending Team Decision

These files were moved here during a repository cleanup because their purpose or necessity is unclear. Please review each one and decide whether to **keep** (move it back), **refactor** (integrate into the main codebase), or **delete**.

---

## Files

### `checkmate_flow_analysis.svg`
- **What it is**: An SVG diagram of the CheckMate pipeline flow.
- **Why it's here**: The diagram is titled "CheckMate document processing pipeline **with annotated issues**" — it contains debug-level annotations highlighting gaps and design decisions, making it unsuitable as a user-facing architecture diagram. It also uses the "Anthropic Sans" font, indicating it was AI-generated.
- **Decision needed**: Should this be cleaned up and used as the official architecture diagram? Or should a new one be created from scratch?

### `generate_ai_report.py`
- **What it is**: A standalone 178-line Python script that runs the full forensic pipeline (ingestion → ELA → metadata → seal → NLP → fusion → AI investigation) on a single document.
- **Why it's here**: It duplicates logic already orchestrated by `backend/workers/pipeline_worker.py` and exposed via the CLI (`python -m checkmate_cli analyze`). It may have been an early prototype or a convenience script for testing.
- **Decision needed**: Is this still useful as a standalone utility, or is the CLI the canonical way to run analysis?

### `install.ps1`
- **What it is**: A PowerShell setup script (3,387 bytes) that automates virtual environment creation and dependency installation on Windows.
- **Why it's here**: The project now has a comprehensive `docs/setup.md` guide that covers Windows, Linux, and macOS. This script may be outdated or redundant.
- **Decision needed**: Is this still maintained and tested? If yes, move it back to root or to a `scripts/` directory. If not, delete it.

### `install.sh`
- **What it is**: A Bash setup script (2,971 bytes) that automates virtual environment creation and dependency installation on Linux/macOS.
- **Why it's here**: Same reasoning as `install.ps1` — the `docs/setup.md` guide now covers this. The script may be outdated.
- **Decision needed**: Same as above — keep if maintained, delete if not.
