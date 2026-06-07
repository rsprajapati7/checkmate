from fastapi import APIRouter
router = APIRouter(prefix="/v1/reports", tags=["reports"])

@router.get("/{job_id}")
async def get_report(job_id: str):
    """Retrieve final report PDF or JSON summary"""
    return {"job_id": job_id, "score": 15, "tier": "GREEN"}
