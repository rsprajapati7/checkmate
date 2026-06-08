"""Full upload route — saves file to disk, creates DB records, returns job_id."""
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import Document, Job, JobStatus
from backend.core.storage import save_upload, get_output_dir
from backend.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from backend.core.logger import get_logger
from backend.workers.pipeline_worker import run_pipeline

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_BYTES = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024


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
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_TYPES}")

    file_bytes = await file.read()

    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {settings.UPLOAD_MAX_SIZE_MB}MB")

    # Save to disk
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    try:
        file_path = save_upload(file_bytes, file.filename)
    except Exception as e:
        logger.error(f"File save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create DB records
    doc = Document(
        id=doc_id,
        filename=file.filename,
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

    logger.info(f"[Upload] File: {file.filename} | Job: {job_id}")

    return JSONResponse({
        "job_id": job_id,
        "document_id": doc_id,
        "filename": file.filename,
        "status": "queued",
        "status_url": f"/api/v1/jobs/{job_id}",
        "report_url": f"/api/v1/reports/{job_id}",
    })


async def _run_pipeline_task(job_id: str, document_id: str, file_path: str):
    """Wrapper to run pipeline in its own DB session (BackgroundTask context)."""
    from backend.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await run_pipeline(job_id, document_id, file_path, session)
