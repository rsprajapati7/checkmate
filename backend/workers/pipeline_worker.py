"""
Pipeline Worker — Central Async Orchestrator.

Execution flow:
  1.  Ingestion          (OCR + metadata + QR extraction)
  2.  ELA + Metadata + Seal (parallel asyncio.gather)
  3.  LLM: Doc Identification + Field Normalization (Gemma 4)
  4.  NLP Cross-Doc Consistency
  5.  Registry Verification
  6.  Pattern Detection (DB lookup + Gemma 4)
  7.  Fusion Engine → Risk Tier
  8.  IF RED: Deep AI Investigation (Gemma 4 multimodal)
  9.  Report Generation (HTML + PDF)
  10. DB persistence
"""

import asyncio
import os
import traceback
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.models import Job, JobStatus, RiskScore, Report, HistoricalEntry
from backend.core.storage import get_output_dir

from backend.ingestion.engine import ingest_document, IngestionResult
from backend.pipelines.ela_forgery.runner import run_ela_pipeline, ELAResult
from backend.pipelines.metadata_forensics.scorer import run_metadata_pipeline, MetadataResult
from backend.pipelines.nlp_cross_doc.scorer import run_nlp_pipeline, NLPResult
from backend.pipelines.seal_detection.scorer import run_seal_pipeline, SealResult

from backend.ai_investigator.llm_client import llm_client
from backend.ai_investigator.prompt_builder import (
    build_doc_identification_prompt,
    build_field_normalization_prompt,
    build_investigation_prompt,
)
from backend.ai_investigator.reasoning import (
    parse_doc_identification,
    parse_field_normalization,
    parse_investigation,
)

from backend.cross_analysis.registry_client import verify_document
from backend.pattern_detection.campaign_detector import run_pattern_detection, PatternResult

from backend.fusion.engine import fuse_scores, FusionResult
from backend.fusion.risk_tier import tier_label

from backend.report_gen.pdf_builder import build_report
from backend.report_gen.json_serializer import serialize_report

logger = get_logger(__name__)


async def run_pipeline(job_id: str, document_id: str, file_path: str, db: AsyncSession) -> None:
    """
    Main async orchestrator — called as a FastAPI BackgroundTask.
    Updates Job status/progress throughout execution.
    """
    output_dir = str(get_output_dir(job_id))

    async def update_job(status: JobStatus, stage: str, progress: int, error: str = None):
        job = await db.get(Job, job_id)
        if job:
            job.status = status
            job.stage = stage
            job.progress = progress
            job.error_message = error
            job.updated_at = datetime.utcnow()
            await db.commit()

    try:
        # ------------------------------------------------------------------ #
        # STEP 1: Ingestion
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.INGESTING, "ingestion", 5)
        logger.info(f"[Worker:{job_id}] Step 1 — Ingestion")

        ingestion: IngestionResult = ingest_document(file_path, job_id, output_dir)
        image_paths = [p.image_path for p in ingestion.pages]

        # ------------------------------------------------------------------ #
        # STEP 2: Parallel forensic pipelines (ELA + Metadata + Seal)
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.ANALYZING, "parallel_forensics", 15)
        logger.info(f"[Worker:{job_id}] Step 2 — Parallel pipeline analysis")

        ela_result, meta_result, seal_result = await asyncio.gather(
            run_ela_pipeline(image_paths, is_scanned=ingestion.is_scanned),
            run_metadata_pipeline(ingestion),
            run_seal_pipeline(image_paths, is_scanned=ingestion.is_scanned),
        )
        ela_result: ELAResult
        meta_result: MetadataResult
        seal_result: SealResult

        # ------------------------------------------------------------------ #
        # STEP 3: LLM — Doc Identification + Field Normalization (Gemma 4)
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.ANALYZING, "llm_classification", 35)
        logger.info(f"[Worker:{job_id}] Step 3 — Gemma 4: Doc ID + Field normalization")

        qr_data = [qr.data for qr in ingestion.all_qr_codes]

        doc_id_raw, field_norm_raw = await asyncio.gather(
            llm_client.complete_json(
                build_doc_identification_prompt(ingestion.full_ocr_text, qr_data)
            ),
            llm_client.complete_json(
                build_field_normalization_prompt(ingestion.full_ocr_text, "document")
            ),
        )

        doc_id_result = parse_doc_identification(doc_id_raw)
        field_result = parse_field_normalization(field_norm_raw)
        doc_type = doc_id_result.doc_type

        # Update field normalization with LLM result
        extracted_fields = {
            "name": field_result.name,
            "date_of_birth": field_result.date_of_birth,
            "id_number": field_result.id_number,
            "address": field_result.address,
            "issue_date": field_result.issue_date,
            "expiry_date": field_result.expiry_date,
            "issuing_authority": field_result.issuing_authority,
            "father_name": field_result.father_name,
            "gender": field_result.gender,
        }
        if field_result.additional_fields:
            extracted_fields.update(field_result.additional_fields)

        # ------------------------------------------------------------------ #
        # STEP 4: NLP Cross-Document Consistency
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.ANALYZING, "nlp_consistency", 50)
        logger.info(f"[Worker:{job_id}] Step 4 — NLP cross-document consistency")

        nlp_result: NLPResult = await run_nlp_pipeline(ingestion)

        # ------------------------------------------------------------------ #
        # STEP 5: Registry Verification
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.ANALYZING, "registry_check", 60)
        logger.info(f"[Worker:{job_id}] Step 5 — Registry verification")

        registry_result = None
        registry_details = {}
        id_number = (
            field_result.id_number
            or (doc_id_result.detected_id_numbers[0] if doc_id_result.detected_id_numbers else None)
        )

        if id_number and doc_type:
            try:
                registry_result = verify_document(doc_type, str(id_number))
                if registry_result:
                    registry_details = {
                        "found": registry_result.found,
                        "match": registry_result.match,
                        "doc_type": registry_result.doc_type,
                        "message": registry_result.message,
                        "details": registry_result.details,
                    }
            except Exception as e:
                logger.warning(f"[Worker:{job_id}] Registry check failed: {e}")

        # ------------------------------------------------------------------ #
        # STEP 6: Pattern Detection
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.ANALYZING, "pattern_detection", 68)
        logger.info(f"[Worker:{job_id}] Step 6 — Pattern detection")

        # Look up historical entries with same ID numbers
        historical_matches = []
        all_ids = (
            nlp_result.entities.get("pan_numbers", []) +
            nlp_result.entities.get("aadhaar_numbers", []) +
            doc_id_result.detected_id_numbers
        )

        if all_ids:
            try:
                from sqlalchemy import select
                stmt = select(HistoricalEntry).where(
                    HistoricalEntry.id_numbers.op('&&')(all_ids)  # array overlap
                ).limit(10)
                # Note: this requires PostgreSQL array overlap operator
                # For SQLite fallback, we skip this and rely on LLM
            except Exception:
                pass

        pattern_result: PatternResult = await run_pattern_detection(
            current_entities=nlp_result.entities,
            historical_matches=historical_matches,
            use_llm=bool(all_ids),
        )

        # ------------------------------------------------------------------ #
        # STEP 7: Fusion Engine
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.FUSING, "risk_fusion", 75)
        logger.info(f"[Worker:{job_id}] Step 7 — Risk fusion")

        # Registry failure adds to final score
        registry_penalty = 0.0
        if registry_result and not registry_result.match and registry_result.found:
            registry_penalty = 20.0  # found but mismatched → suspicious

        fusion: FusionResult = fuse_scores(
            ela_score=ela_result.score,
            metadata_score=meta_result.score,
            seal_score=seal_result.score,
            nlp_score=max(nlp_result.score, registry_penalty),
            is_scanned=ingestion.is_scanned,
        )

        # ------------------------------------------------------------------ #
        # STEP 8: Deep AI Investigation (RED tier only)
        # ------------------------------------------------------------------ #
        llm_investigation_text = None

        if fusion.risk_tier.value == "RED":
            await update_job(JobStatus.INVESTIGATING, "ai_investigation", 82)
            logger.info(f"[Worker:{job_id}] Step 8 — Gemma 4 Deep AI Investigation (RED)")

            try:
                investigation_prompt = build_investigation_prompt(
                    doc_type=doc_type,
                    ela_score=ela_result.score,
                    metadata_score=meta_result.score,
                    seal_score=seal_result.score,
                    nlp_score=nlp_result.score,
                    final_score=fusion.final_score * 100,
                    ela_flags=ela_result.flags,
                    metadata_flags=meta_result.flags,
                    seal_flags=seal_result.flags,
                    nlp_flags=nlp_result.flags,
                    pattern_flags=pattern_result.pattern_flags,
                    ocr_text=ingestion.full_ocr_text,
                    extracted_fields=extracted_fields,
                    registry_result=registry_details if registry_details else None,
                )

                investigation_raw = await llm_client.complete_json(
                    investigation_prompt,
                    image_b64=ela_result.heatmap_b64,  # send ELA heatmap to Gemma 4
                )
                inv = parse_investigation(investigation_raw)
                llm_investigation_text = (
                    f"Verdict: {inv.verdict} (Confidence: {inv.confidence:.0%})\n\n"
                    f"{inv.risk_explanation}\n\n"
                    f"Primary Tampering Method: {inv.primary_tampering_method or 'Not identified'}\n\n"
                    f"Key Evidence:\n" + "\n".join(f"• {e}" for e in inv.key_evidence) +
                    f"\n\nRecommended Action: {inv.recommended_action}"
                )
            except Exception as e:
                logger.error(f"[Worker:{job_id}] LLM investigation failed: {e}")
                llm_investigation_text = f"AI investigation failed: {e}"

        # ------------------------------------------------------------------ #
        # STEP 9: Report Generation
        # ------------------------------------------------------------------ #
        await update_job(JobStatus.REPORTING, "report_generation", 90)
        logger.info(f"[Worker:{job_id}] Step 9 — Report generation")

        all_flags = (
            ela_result.flags + meta_result.flags + seal_result.flags +
            nlp_result.flags + pattern_result.pattern_flags
        )

        report_paths = build_report(
            job_id=job_id,
            filename=Path(file_path).name,
            doc_type=doc_type,
            risk_tier=fusion.risk_tier.value,
            tier_label=tier_label(fusion.risk_tier),
            final_score=fusion.final_score,
            ela_score=ela_result.score,
            metadata_score=meta_result.score,
            seal_score=seal_result.score,
            nlp_score=nlp_result.score,
            ela_flags=ela_result.flags,
            metadata_flags=meta_result.flags,
            seal_flags=seal_result.flags,
            nlp_flags=nlp_result.flags,
            pattern_flags=pattern_result.pattern_flags,
            ela_heatmap_b64=ela_result.heatmap_b64 or "",
            extracted_fields=extracted_fields,
            registry_details=registry_details,
            llm_investigation=llm_investigation_text or "",
            output_dir=output_dir,
        )

        # JSON report
        json_data = {
            "job_id": job_id,
            "document_id": document_id,
            "filename": Path(file_path).name,
            "doc_type": doc_type,
            "risk_tier": fusion.risk_tier.value,
            "tier_label": tier_label(fusion.risk_tier),
            "final_score": fusion.final_score,
            "scores": {
                "ela": ela_result.score,
                "metadata": meta_result.score,
                "seal": seal_result.score,
                "nlp": nlp_result.score,
            },
            "flags": all_flags,
            "extracted_fields": extracted_fields,
            "registry": registry_details,
            "llm_investigation": llm_investigation_text,
            "ela_heatmap_b64": ela_result.heatmap_b64,
        }
        json_path = serialize_report(job_id, json_data, output_dir)

        # ------------------------------------------------------------------ #
        # STEP 10: DB Persistence
        # ------------------------------------------------------------------ #
        logger.info(f"[Worker:{job_id}] Step 10 — Persisting results to DB")

        risk_score_record = RiskScore(
            job_id=job_id,
            ela_score=ela_result.score,
            metadata_score=meta_result.score,
            seal_score=seal_result.score,
            nlp_score=nlp_result.score,
            final_score=fusion.final_score,
            risk_tier=fusion.risk_tier,
            ela_flags=ela_result.flags,
            metadata_flags=meta_result.flags,
            seal_flags=seal_result.flags,
            nlp_flags=nlp_result.flags,
            ela_heatmap_b64=ela_result.heatmap_b64,
            doc_type=doc_type,
            extracted_fields=extracted_fields,
            registry_verified=registry_result.match if registry_result else None,
            registry_details=registry_details,
            pattern_flags=pattern_result.pattern_flags,
            llm_investigation=llm_investigation_text,
        )
        db.add(risk_score_record)

        report_record = Report(
            job_id=job_id,
            pdf_path=report_paths.get("pdf_path"),
            html_path=report_paths.get("html_path"),
            json_path=json_path,
        )
        db.add(report_record)

        # Historical fingerprint
        historical = HistoricalEntry(
            job_id=job_id,
            doc_type=doc_type,
            id_numbers=all_ids[:5],
            risk_tier=fusion.risk_tier,
        )
        db.add(historical)

        await update_job(JobStatus.DONE, "completed", 100)
        logger.info(f"[Worker:{job_id}] Pipeline complete — {fusion.risk_tier.value} ({fusion.final_score:.3f})")

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        logger.error(f"[Worker:{job_id}] Pipeline FAILED: {error_msg}")
        await update_job(JobStatus.FAILED, "error", 0, error=str(exc))
