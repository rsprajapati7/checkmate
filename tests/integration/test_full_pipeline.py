import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.core.models import (
    Base, Document, Job, RiskScore, Report, HistoricalEntry, RiskTier, JobStatus
)
from backend.workers.pipeline_worker import run_pipeline
from backend.ingestion.engine import IngestionResult, PageData
from backend.pipelines.ela_forgery.runner import ELAResult
from backend.pipelines.metadata_forensics.scorer import MetadataResult
from backend.pipelines.seal_detection.scorer import SealResult
from backend.pipelines.nlp_cross_doc.scorer import NLPResult
from backend.pattern_detection.campaign_detector import PatternResult


@pytest.mark.anyio
async def test_run_pipeline_success():
    # 1. Initialize DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Add initial records
    async with async_session() as session:
        doc = Document(
            id="doc-123",
            filename="user_doc.pdf",
            file_path="/tmp/user_doc.pdf",
            file_type="PDF"
        )
        job = Job(
            id="job-123",
            document_id="doc-123",
            status=JobStatus.PENDING,
            stage="queued"
        )
        session.add_all([doc, job])
        await session.commit()

    # 3. Setup Mocks
    mock_ingestion = IngestionResult(
        document_id="doc-123",
        file_path="/tmp/user_doc.pdf",
        file_type="PDF",
        file_size_bytes=1024,
        is_scanned=False,
        page_count=1,
        pages=[PageData(page_num=1, image_path="/tmp/page1.jpg", ocr_text="Dummy OCR", native_text="Dummy Native")],
        full_ocr_text="Dummy OCR",
        full_native_text="Dummy Native",
        all_qr_codes=[]
    )

    mock_ela = ELAResult(
        score=10.0,
        risk_label="LOW",
        heatmap_b64="base64heatmap",
        anomalous_regions=0,
        flags=[],
        per_page_scores=[10.0]
    )

    mock_meta = MetadataResult(
        score=20.0,
        flags=[],
        raw_metadata={"producer": "Adobe Acrobat"}
    )

    mock_seal = SealResult(
        score=0.0,
        seals_found=0,
        suspicious_seals=0,
        flags=[]
    )

    mock_nlp = NLPResult(
        score=15.0,
        flags=[],
        entities={"names": ["John Doe"]}
    )

    mock_pattern = PatternResult(
        reuse_detected=False,
        campaign_suspected=False,
        confidence=0.0,
        pattern_flags=[],
        explanation=""
    )

    # Mock the LLM calls to return structured JSON
    # doc identification returns doc_type and detected_id_numbers
    # field normalization returns names etc.
    llm_doc_id = {"doc_type": "ITR", "confidence": 0.9, "detected_id_numbers": []}
    llm_field_norm = {"name": "John Doe", "id_number": "ABCDE1234F"}

    # Mock build_report and serialize_report
    mock_report_paths = {"pdf_path": "/tmp/out.pdf", "html_path": "/tmp/out.html"}

    # Run execution with patched imports
    with patch("backend.workers.pipeline_worker.ingest_document", return_value=mock_ingestion), \
         patch("backend.workers.pipeline_worker.run_ela_pipeline", return_value=mock_ela), \
         patch("backend.workers.pipeline_worker.run_metadata_pipeline", return_value=mock_meta), \
         patch("backend.workers.pipeline_worker.run_seal_pipeline", return_value=mock_seal), \
         patch("backend.workers.pipeline_worker.run_nlp_pipeline", return_value=mock_nlp), \
         patch("backend.workers.pipeline_worker.run_pattern_detection", return_value=mock_pattern), \
         patch("backend.workers.pipeline_worker.llm_client.complete_json") as mock_complete_json, \
         patch("backend.workers.pipeline_worker.build_report", return_value=mock_report_paths), \
         patch("backend.workers.pipeline_worker.serialize_report", return_value="/tmp/out.json"), \
         patch("backend.core.storage.cleanup_job_temp") as mock_cleanup, \
         patch("backend.core.storage.delete_file") as mock_delete, \
         patch("backend.workers.pipeline_worker.verify_document", return_value=None):
        
        # Make complete_json return doc id first, then field normalization
        mock_complete_json.side_effect = [llm_doc_id, llm_field_norm]

        async with async_session() as session:
            await run_pipeline(
                job_id="job-123",
                document_id="doc-123",
                file_path="/tmp/user_doc.pdf",
                db=session
            )

        # Assert cleanup calls were executed
        mock_cleanup.assert_called_once_with("job-123")
        mock_delete.assert_called_once_with("/tmp/user_doc.pdf")

    # 4. Verify DB changes
    async with async_session() as session:
        # Check Job Status
        stmt = select(Job).where(Job.id == "job-123")
        result = await session.execute(stmt)
        job = result.scalar_one()
        assert job.status == JobStatus.DONE
        assert job.progress == 100

        # Check Risk Score
        stmt_risk = select(RiskScore).where(RiskScore.job_id == "job-123")
        result_risk = await session.execute(stmt_risk)
        risk = result_risk.scalar_one()
        assert risk.ela_score == 10.0
        assert risk.metadata_score == 20.0
        assert risk.seal_score == 0.0
        assert risk.nlp_score == 15.0
        assert risk.doc_type == "ITR"
        assert risk.risk_tier == RiskTier.GREEN

        # Check Report
        stmt_report = select(Report).where(Report.job_id == "job-123")
        result_report = await session.execute(stmt_report)
        report = result_report.scalar_one()
        assert report.pdf_path == "/tmp/out.pdf"
        assert report.html_path == "/tmp/out.html"
        assert report.json_path == "/tmp/out.json"

        # Check HistoricalEntry
        stmt_hist = select(HistoricalEntry).where(HistoricalEntry.job_id == "job-123")
        result_hist = await session.execute(stmt_hist)
        hist = result_hist.scalar_one()
        assert hist.doc_type == "ITR"

    await engine.dispose()