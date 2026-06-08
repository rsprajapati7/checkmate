"""Report retrieval routes — JSON and PDF download."""
import os

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.core.models import Job, JobStatus, RiskScore, Report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{job_id}")
async def get_report(job_id: str, db: AsyncSession = Depends(get_db)):
    """Return the full JSON analysis report for a completed job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.status != JobStatus.DONE:
        raise HTTPException(
            status_code=202,
            detail=f"Job not complete yet. Status: {job.status.value} ({job.progress}%)"
        )

    # Fetch risk score
    result = await db.execute(select(RiskScore).where(RiskScore.job_id == job_id))
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk score record not found")

    return JSONResponse({
        "job_id": job_id,
        "document_id": job.document_id,
        "risk_tier": risk.risk_tier.value,
        "final_score": risk.final_score,
        "doc_type": risk.doc_type,
        "scores": {
            "ela": risk.ela_score,
            "metadata": risk.metadata_score,
            "seal": risk.seal_score,
            "nlp": risk.nlp_score,
        },
        "flags": {
            "ela": risk.ela_flags,
            "metadata": risk.metadata_flags,
            "seal": risk.seal_flags,
            "nlp": risk.nlp_flags,
            "pattern": risk.pattern_flags,
        },
        "extracted_fields": risk.extracted_fields,
        "registry_verified": risk.registry_verified,
        "registry_details": risk.registry_details,
        "ela_heatmap_b64": risk.ela_heatmap_b64,
        "llm_investigation": risk.llm_investigation,
    })


@router.get("/{job_id}/pdf")
async def download_pdf_report(job_id: str, db: AsyncSession = Depends(get_db)):
    """Download the PDF forensic report."""
    job = await db.get(Job, job_id)
    if not job or job.status != JobStatus.DONE:
        raise HTTPException(status_code=404, detail="Report not ready or job not found")

    result = await db.execute(select(Report).where(Report.job_id == job_id))
    report = result.scalar_one_or_none()

    if not report or not report.pdf_path or not os.path.exists(report.pdf_path):
        # Fall back to HTML
        if report and report.html_path and os.path.exists(report.html_path):
            return FileResponse(report.html_path, media_type="text/html",
                                filename=f"checkmate_report_{job_id}.html")
        raise HTTPException(status_code=404, detail="PDF report not available")

    return FileResponse(
        report.pdf_path,
        media_type="application/pdf",
        filename=f"checkmate_report_{job_id}.pdf"
    )
