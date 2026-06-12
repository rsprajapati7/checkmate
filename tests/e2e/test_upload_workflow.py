import pytest
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from backend.main import app
from backend.core.config import settings
from backend.core.models import Job, JobStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_and_pipeline_workflow(client):
    # 1. Prepare a mock file to upload (a tiny PDF with %PDF magic header)
    pdf_content = b"%PDF-1.4\n%mock pdf content for testing e2e workflow"
    file_name = "test_upload_doc.pdf"

    # 2. Mock external services: LLM, registry verification
    mock_llm_doc_id = {"doc_type": "PAN", "confidence": 0.95, "detected_id_numbers": ["ABCDE1234F"]}
    mock_llm_field_norm = {"name": "Jane Doe", "id_number": "ABCDE1234F"}
    
    mock_report_paths = {"pdf_path": "/tmp/test_out.pdf", "html_path": "/tmp/test_out.html"}

    # We mock pymupdf or document ingestion to avoid actually parsing on test runners
    # We mock PyMuPDF document loading and pages
    mock_page = MagicMock()
    mock_page.get_text.return_value = "ABCDE1234F Jane Doe PAN Card"
    mock_page.rect = MagicMock()
    mock_page.rect.width = 100
    mock_page.rect.height = 100
    # mock pixmap
    mock_pix = MagicMock()
    mock_pix.width = 100
    mock_pix.height = 100
    mock_pix.samples = b"\x00" * 30000
    mock_page.get_pixmap.return_value = mock_pix

    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.metadata = {}
    mock_doc.get_xml_metadata.return_value = ""

    with patch("backend.ingestion.engine.pymupdf.open", return_value=mock_doc), \
         patch("backend.ingestion.engine.extract_qr_from_pages", return_value=[]), \
         patch("backend.ingestion.engine.run_tesseract", return_value="ABCDE1234F Jane Doe PAN Card"), \
         patch("backend.workers.pipeline_worker.llm_client.complete_json") as mock_complete_json, \
         patch("backend.workers.pipeline_worker.verify_document") as mock_verify_doc, \
         patch("backend.workers.pipeline_worker.build_report", return_value=mock_report_paths), \
         patch("backend.workers.pipeline_worker.serialize_report", return_value="/tmp/test_out.json"), \
         patch("backend.core.storage.cleanup_job_temp") as mock_cleanup, \
         patch("backend.core.storage.delete_file") as mock_delete:

        mock_complete_json.side_effect = [mock_llm_doc_id, mock_llm_field_norm]
        
        mock_reg_result = MagicMock()
        mock_reg_result.found = True
        mock_reg_result.match = True
        mock_reg_result.doc_type = "PAN"
        mock_reg_result.message = "Verified"
        mock_reg_result.details = {}
        mock_verify_doc.return_value = mock_reg_result

        # 3. Perform the upload request
        # Bypass API key check by setting it to empty in config
        with patch.object(settings, "API_KEY_SECRET", ""):
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": (file_name, io.BytesIO(pdf_content), "application/pdf")}
            )
            
            assert response.status_code == 200
            res_data = response.json()
            assert "job_id" in res_data
            assert "document_id" in res_data
            assert res_data["status"] == "queued"
            
            job_id = res_data["job_id"]
            
            # Since TestClient runs background tasks synchronously, by the time post() returns,
            # the background pipeline should have run and completed!
            
            # 4. Check status polling endpoint
            status_response = client.get(f"/api/v1/jobs/{job_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] == "DONE"
            assert status_data["progress"] == 100
            
            # 5. Check report retrieval endpoint
            report_response = client.get(f"/api/v1/reports/{job_id}")
            assert report_response.status_code == 200
            report_data = report_response.json()
            assert report_data["job_id"] == job_id
            assert report_data["risk_tier"] == "GREEN"
            assert report_data["doc_type"] == "PAN"
            assert report_data["extracted_fields"]["name"] == "Jane Doe"
            assert report_data["registry_verified"] is True