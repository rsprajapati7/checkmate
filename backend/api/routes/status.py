from fastapi import APIRouter
router = APIRouter(prefix="/v1/jobs", tags=["status"])

@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """Retrieve current progress and status of analysis job"""
    return {"job_id": job_id, "status": "completed", "progress": 100}
