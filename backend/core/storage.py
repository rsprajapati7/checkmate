import os
import shutil
import uuid
from pathlib import Path

from backend.core.config import settings


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_upload(file_bytes: bytes, filename: str) -> str:
    """Save uploaded file bytes to the temp upload directory. Returns file path."""
    upload_dir = _ensure_dir(settings.UPLOAD_TEMP_DIR)
    unique_name = f"{uuid.uuid4()}_{filename}"
    dest = upload_dir / unique_name
    dest.write_bytes(file_bytes)
    return str(dest)


def get_output_dir(job_id: str) -> Path:
    """Return (and create) the output directory for a specific job."""
    return _ensure_dir(os.path.join(settings.OUTPUT_DIR, job_id))


def delete_file(path: str) -> None:
    """Delete a file if it exists."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def cleanup_job_temp(job_id: str) -> None:
    """Remove the job output directory after report is finalized."""
    job_dir = Path(settings.OUTPUT_DIR) / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


def file_exists(path: str) -> bool:
    return Path(path).exists()
