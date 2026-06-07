from fastapi import APIRouter
router = APIRouter(prefix="/v1/documents", tags=["analysis"])

@router.post("/{doc_id}/analyze")
async def analyze_document(doc_id: str):
    """Trigger forensic pipeline analysis on the uploaded document"""
    return {"status": "processing", "job_id": "job_123", "document_id": doc_id}
