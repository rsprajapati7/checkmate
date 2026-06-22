import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.core.models import (
    Base, Document, Job, RiskScore, Report, HistoricalEntry, RiskTier, JobStatus
)


@pytest.mark.anyio
async def test_db_operations():
    # 1. Initialize an in-memory SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # 2. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Perform database operations
    async with async_session() as session:
        # Create Document
        doc = Document(
            filename="test_doc.pdf",
            file_path="/tmp/test_doc.pdf",
            file_size_bytes=1024,
            file_type="PDF",
            is_scanned=True,
            page_count=2
        )
        session.add(doc)
        await session.commit()
        doc_id = doc.id
        assert doc_id is not None

        # Create Job
        job = Job(
            document_id=doc_id,
            status=JobStatus.INGESTING,
            stage="ingestion",
            progress=10
        )
        session.add(job)
        await session.commit()
        job_id = job.id
        assert job_id is not None

        # Verify Document relationship using selectinload
        stmt = select(Document).where(Document.id == doc_id).options(selectinload(Document.jobs))
        result = await session.execute(stmt)
        refreshed_doc = result.scalar_one()
        assert len(refreshed_doc.jobs) == 1
        assert refreshed_doc.jobs[0].id == job_id

        # Create RiskScore
        risk = RiskScore(
            job_id=job_id,
            ela_score=15.0,
            metadata_score=45.0,
            seal_score=0.0,
            nlp_score=10.0,
            final_score=0.25,
            risk_tier=RiskTier.GREEN,
            ela_flags=["SUSPICIOUS_ELA_PEAK"],
            metadata_flags=[],
            extracted_fields={"name": "Alice"},
            registry_verified=True
        )
        session.add(risk)

        # Create Report
        report = Report(
            job_id=job_id,
            pdf_path="/tmp/report.pdf",
            html_path="/tmp/report.html",
            json_path="/tmp/report.json"
        )
        session.add(report)

        # Create HistoricalEntry
        hist = HistoricalEntry(
            job_id=job_id,
            doc_type="ITR",
            id_numbers=["ABCDE1234F"],
            risk_tier=RiskTier.GREEN
        )
        session.add(hist)
        await session.commit()

    # 4. Read back and verify relationships
    async with async_session() as session:
        # Query Job and load relationships eagerly
        stmt = select(Job).where(Job.id == job_id).options(
            selectinload(Job.document),
            selectinload(Job.risk_score),
            selectinload(Job.report)
        )
        result = await session.execute(stmt)
        queried_job = result.scalar_one()

        assert queried_job.status == JobStatus.INGESTING
        assert queried_job.document.filename == "test_doc.pdf"

        # Verify RiskScore
        assert queried_job.risk_score is not None
        assert queried_job.risk_score.final_score == 0.25
        assert queried_job.risk_score.risk_tier == RiskTier.GREEN
        assert queried_job.risk_score.ela_flags == ["SUSPICIOUS_ELA_PEAK"]
        assert queried_job.risk_score.extracted_fields == {"name": "Alice"}
        assert queried_job.risk_score.registry_verified is True

        # Verify Report
        assert queried_job.report is not None
        assert queried_job.report.pdf_path == "/tmp/report.pdf"

        # Verify HistoricalEntry
        stmt_hist = select(HistoricalEntry).where(HistoricalEntry.job_id == job_id)
        res_hist = await session.execute(stmt_hist)
        queried_hist = res_hist.scalar_one()
        assert queried_hist.doc_type == "ITR"
        assert queried_hist.id_numbers == ["ABCDE1234F"]

    await engine.dispose()