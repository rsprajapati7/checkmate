"""Full upload route — saves file to disk, creates DB records, returns job_id."""
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db, AsyncSessionLocal
from backend.core.models import Document, Job, JobStatus
from backend.core.storage import save_upload, get_output_dir
from backend.core.security import sanitize_filename
from backend.core.logger import get_logger
from backend.workers.pipeline_worker import run_pipeline

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_BYTES = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024

# Allowed MIME type magic bytes (first few bytes of each format)
_MAGIC = {
    b"%PDF": ".pdf",
    b"\x89PNG": ".png",
    b"\xff\xd8\xff": ".jpg",  # JPEG (also covers .jpeg)
}


def _validate_mime(file_bytes: bytes, declared_ext: str) -> None:
    """
    Check file magic bytes to confirm the content matches the declared extension.
    Raises HTTPException 400 if there is a mismatch.
    """
    header = file_bytes[:8]
    for magic, ext in _MAGIC.items():
        if header.startswith(magic):
            # JPEG magic covers both .jpg and .jpeg
            if ext == ".jpg" and declared_ext in (".jpg", ".jpeg"):
                return
            if ext == declared_ext:
                return
            raise HTTPException(
                status_code=400,
                detail=f"File content does not match declared extension '{declared_ext}'",
            )
    raise HTTPException(
        status_code=400,
        detail=f"Unrecognized file format. Allowed: PDF, PNG, JPG",
    )


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document (PDF/PNG/JPG) and trigger async forensic analysis.
    Returns { job_id, document_id, status_url }
    """
    # --- Filename validation ---
    try:
        safe_name = sanitize_filename(file.filename or "upload")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {sorted(ALLOWED_TYPES)}",
        )

    chunks = []
    total_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunks
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.UPLOAD_MAX_SIZE_MB} MB",
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    # --- Magic byte validation ---
    _validate_mime(file_bytes, ext)

    # Save to disk using the sanitized filename
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    try:
        file_path = save_upload(file_bytes, safe_name)
    except Exception as e:
        logger.error("File save failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create DB records
    doc = Document(
        id=doc_id,
        filename=safe_name,
        file_path=file_path,
        file_size_bytes=len(file_bytes),
        file_type=ext.replace(".", "").upper(),
    )
    db.add(doc)

    job = Job(id=job_id, document_id=doc_id, status=JobStatus.PENDING, stage="queued")
    db.add(job)
    await db.commit()

    # Queue async pipeline
    background_tasks.add_task(_run_pipeline_task, job_id, doc_id, file_path)

    logger.info("[Upload] File: %s | Job: %s", safe_name, job_id)

    return JSONResponse({
        "job_id": job_id,
        "document_id": doc_id,
        "filename": safe_name,
        "status": "queued",
        "status_url": f"/api/v1/jobs/{job_id}",
        "report_url": f"/api/v1/reports/{job_id}",
    })


async def _run_pipeline_task(job_id: str, document_id: str, file_path: str) -> None:
    """
    Wrapper to run pipeline in its own DB session (BackgroundTask context).
    Ensures the job is marked FAILED even if the pipeline worker itself crashes.
    """
    async with AsyncSessionLocal() as session:
        try:
            await run_pipeline(job_id, document_id, file_path, session)
        except Exception as e:
            logger.error("Background pipeline task crashed for job %s: %s", job_id, e)
            # Attempt to persist the failure so the job is not left stuck in PENDING
            try:
                job = await session.get(Job, job_id)
                if job and job.status not in (JobStatus.DONE, JobStatus.FAILED):
                    job.status = JobStatus.FAILED
                    job.error_message = f"Unhandled pipeline crash: {e}"
                    await session.commit()
            except Exception as db_err:
                logger.critical(
                    "Could not persist failure state for job %s: %s", job_id, db_err
                )
