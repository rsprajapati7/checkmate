# Implementation Plan — Pipeline Data Format & False Positive Alignment

We need to resolve formatting issues, false positives, and ensure robust data validation across the four forensic pipelines (ELA, Metadata, Seal Detection, NLP Cross-Doc).

## User Review Required

> [!IMPORTANT]
> - ELA pipeline will now convert non-JPEG image sources (e.g. PDF rendered PNGs or direct PNG uploads) to JPEG format (quality 95) in-memory before running ELA to eliminate text-boundary ringing false-positives and silence PyMuPDF/Pillow `UserWarning`s.
> - Seal detection's sharpness threshold is updated: we no longer flag seals as suspicious *solely* for having high sharpness (`lap_var > 800`). Instead, we flag them if they are blurry (`lap_var < 150` — copying low-res seals) or if high sharpness is accompanied by ELA anomaly markers (`lap_var > 1000` AND `ela_score > 4.0`).
> - NLP pipeline will extract and parse structured QR code payloads (JSON/dict/key-value format) and cross-reference their fields (e.g., student name, roll number, or identifier values) against the main document OCR text.

## Proposed Changes

### Ingestion & ELA Pipeline

#### [MODIFY] [ela.py](file:///d:/Code-Base/checkmate/backend/pipelines/ela_forgery/ela.py)
- In `compute_ela`, check if the image suffix is not a JPEG.
- If not a JPEG, convert the image to JPEG format in-memory with quality `95` to establish a baseline JPEG compression grid, then re-save it at the target quality for ELA calculation.
- This mathematically corrects ELA for lossless source inputs.

### Seal Detection Pipeline

#### [MODIFY] [scorer.py](file:///d:/Code-Base/checkmate/backend/pipelines/seal_detection/scorer.py)
- Modify `_crop_ela_score` to convert the cropped image to JPEG at quality 95 in-memory first if the source is not a JPEG.
- Calibrate the suspicion logic in `_run_sync`:
  - Flag as blurry if `lap_var < 150`.
  - Flag as pasted digital seal if `lap_var > 1000` and `ela_score > 4.0`.
  - Flag for high ELA anomaly independently if `ela_score > 6.0`.

#### [MODIFY] [visualize.py](file:///d:/Code-Base/checkmate/backend/pipelines/seal_detection/visualize.py)
- Sync the suspicion check logic (`is_susp`) in `generate_seal_dashboard` with the calibrated scoring rules.

### NLP Cross-Doc Pipeline

#### [MODIFY] [scorer.py](file:///d:/Code-Base/checkmate/backend/pipelines/nlp_cross_doc/scorer.py)
- Implement `parse_qr_data(data: str) -> dict` to safely parse JSON, AST literal dicts, or query/key-value style strings.
- In `_run_sync`, cross-check all parsed QR code fields against the normalized OCR document text. Flag any missing keys/values and increase the risk score.
- Add Aadhaar and GSTIN consistency checks for QR vs OCR.

### Registry Verification & Worker

#### [MODIFY] [registry_client.py](file:///d:/Code-Base/checkmate/backend/cross_analysis/registry_client.py)
- Ensure all functions (`verify_document`, `verify_pan`, `verify_aadhaar`, etc.) explicitly convert inputs to strings and strip them to handle integers or enum inputs gracefully.

#### [MODIFY] [pipeline_worker.py](file:///d:/Code-Base/checkmate/backend/workers/pipeline_worker.py)
- Explicitly convert parameters to string before calling `verify_document`.

### Unit Tests

#### [MODIFY] [test_ela.py](file:///d:/Code-Base/checkmate/tests/unit/test_ela.py)
- Add unit tests verifying ELA computation and formatting.

#### [MODIFY] [test_seal_detection.py](file:///d:/Code-Base/checkmate/tests/unit/test_seal_detection.py)
- Add unit tests verifying seal detection bounding boxes, sharpness score, and ELA logic.

#### [MODIFY] [test_nlp_consistency.py](file:///d:/Code-Base/checkmate/tests/unit/test_nlp_consistency.py)
- Add unit tests verifying entity parsing, QR code parsing, and cross-matching logic.

#### [MODIFY] [test_metadata_fsm.py](file:///d:/Code-Base/checkmate/tests/unit/test_metadata_fsm.py)
- Add unit tests verifying metadata anomaly rules.

#### [MODIFY] [test_fusion_engine.py](file:///d:/Code-Base/checkmate/tests/unit/test_fusion_engine.py)
- Add unit tests verifying fusion logic and risk tiers.

## Verification Plan

### Automated Tests
- Install `pytest` and `pytest-asyncio` inside the virtual environment.
- Run `venv\Scripts\python.exe -m pytest` to run the updated test suite.

### Manual Verification
- Execute `test_all_pipelines.py` to confirm that:
  - `Neeraj-7.pdf` gets a reasonable low ELA risk score (no more false-positive HIGH score on PNG renders).
  - `Roll.jpeg` gets a GREEN seal score (0.0 suspicious seals) and correct QR code key-value cross-verification.
