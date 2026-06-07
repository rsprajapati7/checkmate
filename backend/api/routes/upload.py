from fastapi import APIRouter, UploadFile, File
router = APIRouter(prefix="/v1/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload document endpoint"""
    return {"status": "uploaded", "filename": file.filename, "id": "doc_123"}
