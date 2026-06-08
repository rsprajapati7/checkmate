"""Analyze route — triggers pipeline on existing document (alternative to upload+analyze in one step)."""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.models import Document, Job, JobStatus
import uuid

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/{document_id}/analyze")
async def trigger_analysis(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-trigger forensic analysis on an already-uploaded document."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    job_id = str(uuid.uuid4())
    job = Job(id=job_id, document_id=document_id, status=JobStatus.PENDING, stage="queued")
    db.add(job)
    await db.commit()

    from backend.api.routes.upload import _run_pipeline_task
    background_tasks.add_task(_run_pipeline_task, job_id, document_id, doc.file_path)

    return {
        "job_id": job_id,
        "document_id": document_id,
        "status": "queued",
        "status_url": f"/api/v1/jobs/{job_id}",
    }
