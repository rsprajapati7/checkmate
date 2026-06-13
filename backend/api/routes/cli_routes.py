"""
CLI-optimized routes for the TypeScript CLI client.

POST /api/v1/cli/scan  — Synchronous full pipeline scan (no background task)
POST /api/v1/cli/chat  — Gemma chat with optional document context
"""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.core.storage import save_upload
from backend.ingestion.engine import ingest_document
from backend.pipelines.ela_forgery.runner import run_ela_pipeline
from backend.pipelines.metadata_forensics.scorer import run_metadata_pipeline
from backend.pipelines.seal_detection.scorer import run_seal_pipeline
from backend.pipelines.nlp_cross_doc.scorer import run_nlp_pipeline
from backend.fusion.engine import fuse_scores
from backend.ai_investigator.llm_client import llm_client

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/cli", tags=["cli"])

ALLOWED_TYPES = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_BYTES = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024


# --------------------------------------------------------------------------- #
#  POST /api/v1/cli/scan
# --------------------------------------------------------------------------- #

@router.post("/scan")
async def cli_scan(file: UploadFile = File(...)):
    """
    Synchronous full-pipeline document scan for the CLI client.
    Runs ingestion + ELA + metadata + seal + NLP + fusion inline and returns
    the complete results JSON in a single response.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_TYPES}"
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max: {settings.UPLOAD_MAX_SIZE_MB}MB"
        )

    job_id = "cli_" + str(uuid.uuid4())[:8]
    output_dir = str(Path(settings.OUTPUT_DIR) / job_id)
    os.makedirs(output_dir, exist_ok=True)

    # Save file to disk temporarily
    try:
        file_path = save_upload(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    logger.info(f"[CLI Scan] {file.filename} | job={job_id}")

    try:
        # Step 1 — Ingestion (sync, run in executor)
        loop = asyncio.get_running_loop()
        ingestion = await loop.run_in_executor(
            None, ingest_document, file_path, job_id, output_dir
        )
        image_paths = [p.image_path for p in ingestion.pages]

        # Step 2 — Parallel forensic pipelines
        ela_res, meta_res, seal_res = await asyncio.gather(
            run_ela_pipeline(image_paths, is_scanned=ingestion.is_scanned),
            run_metadata_pipeline(ingestion),
            run_seal_pipeline(image_paths, is_scanned=ingestion.is_scanned),
        )

        # Step 3 — NLP (sequential, depends on ingestion)
        # Note: doc_type unknown at this point in the CLI path; NLP financial guards
        # default to off (empty doc_type) to prevent false positives.
        nlp_res = await run_nlp_pipeline(ingestion)

        # Step 4 — Fusion
        fusion = fuse_scores(
            ela_score=ela_res.score,
            metadata_score=meta_res.score,
            seal_score=seal_res.score,
            nlp_score=nlp_res.score,
            is_scanned=ingestion.is_scanned,
        )

        # Build OCR summary
        ocr_text = " ".join(p.ocr_text or "" for p in ingestion.pages)

        return JSONResponse({
            "filename": file.filename,
            "file_type": ingestion.file_type,
            "page_count": ingestion.page_count,
            "is_scanned": ingestion.is_scanned,
            "risk_tier": fusion.risk_tier.value,
            "final_score": round(fusion.final_score * 100, 1),
            "job_id": job_id,
            "pipelines": {
                "ela": {
                    "score": ela_res.score,
                    "flags": ela_res.flags,
                    "heatmap_b64": ela_res.heatmap_b64,
                },
                "metadata": {
                    "score": meta_res.score,
                    "flags": meta_res.flags,
                },
                "seal": {
                    "score": seal_res.score,
                    "flags": seal_res.flags,
                    "seals_found": seal_res.seals_found,
                    "suspicious": seal_res.suspicious_seals,
                },
                "nlp": {
                    "score": nlp_res.score,
                    "flags": nlp_res.flags,
                    "entities": nlp_res.entities,
                },
            },
            "pdf_metadata": ingestion.pdf_metadata,
            "qr_codes": [
                qr.data if hasattr(qr, "data") else str(qr)
                for qr in (ingestion.all_qr_codes or [])
            ],
            "ocr_summary": ocr_text[:2000] + ("..." if len(ocr_text) > 2000 else ""),
        })

    except Exception as e:
        logger.error(f"[CLI Scan] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------- #
#  POST /api/v1/cli/chat
# --------------------------------------------------------------------------- #

class ChatRequest(BaseModel):
    message: str
    context: dict[str, Any] | None = None
    history: list[dict[str, str]] | None = None


@router.post("/chat")
async def cli_chat(req: ChatRequest):
    """
    Send a message to Gemma with optional document forensic context.
    Returns a streamed plain-text response of tokens.
    """
    system_instruction = (
        "You are CheckMate AI, a senior forensic document investigator. "
        "Analyze document properties and pipeline scores with a clinical, "
        "objective, and authoritative tone. Do not use emojis. "
        "Answer the user's questions concisely and accurately. "
        "Be extremely direct and concise. Limit responses to 2-3 sentences if possible."
    )

    context_str = ""
    if req.context:
        c = req.context
        context_str = (
            f"\nActive Document Context:\n"
            f"- Filename: {c.get('filename', 'Unknown')}\n"
            f"- File Type: {c.get('file_type', '?')}\n"
            f"- Pages: {c.get('page_count', '?')}\n"
            f"- Final Integrated Score: {c.get('final_score', '?')}/100\n"
            f"- Risk Tier: {c.get('risk_tier', '?')}\n"
            f"- ELA Score: {c.get('pipelines', {}).get('ela', {}).get('score', '?')}/100\n"
            f"- Metadata Score: {c.get('pipelines', {}).get('metadata', {}).get('score', '?')}/100\n"
            f"- Seal Score: {c.get('pipelines', {}).get('seal', {}).get('score', '?')}/100\n"
            f"- NLP Score: {c.get('pipelines', {}).get('nlp', {}).get('score', '?')}/100\n"
            f"- OCR Summary:\n{c.get('ocr_summary', '')}\n"
            f"{'─' * 50}\n"
        )

    history_str = ""
    for turn in (req.history or [])[-10:]:
        role = turn.get("role", "user").upper()
        history_str += f"{role}: {turn.get('content', '')}\n"

    prompt = (
        f"{system_instruction}\n\n"
        f"{context_str}\n"
        f"Conversation History:\n{history_str}"
        f"USER: {req.message}\n"
        f"ASSISTANT:"
    )

    async def event_generator():
        if settings.LLM_PROVIDER == "google":
            # Reuse the module-level singleton instead of creating a new client per request
            google_client = llm_client._get_google_client()
            from google.genai import types as genai_types
            try:
                response_stream = await google_client.aio.models.generate_content_stream(
                    model=settings.LLM_MODEL,
                    contents=[prompt],
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=settings.LLM_MAX_TOKENS,
                        temperature=settings.LLM_TEMPERATURE,
                    ),
                )
                async for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
            except Exception as e:
                logger.error("[CLI Chat Stream] Failed: %s", e)
                yield f"\n[Error: {e}]"
        else:
            try:
                response = await llm_client.complete(prompt)
                yield response
            except Exception as e:
                yield f"\n[Error: {e}]"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# --------------------------------------------------------------------------- #
#  POST /api/v1/cli/report
# --------------------------------------------------------------------------- #

class ReportRequest(BaseModel):
    results: dict

@router.post("/report")
async def cli_report(req: ReportRequest):
    """
    Generate PDF/HTML report from CLI scan results and return as file response.
    """
    import tempfile
    from backend.report_gen.pdf_builder import build_report

    res = req.results
    job_id = "cli_rep_" + str(uuid.uuid4())[:8]
    
    pipelines = res.get("pipelines", {})
    ela = pipelines.get("ela", {})
    meta = pipelines.get("metadata", {})
    seal = pipelines.get("seal", {})
    nlp = pipelines.get("nlp", {})
    
    temp_dir = tempfile.gettempdir()
    
    try:
        # Run report builder
        report_res = build_report(
            job_id=job_id,
            filename=res.get("filename", "document"),
            doc_type=res.get("file_type", "PDF"),
            risk_tier=res.get("risk_tier", "GREEN"),
            tier_label="Verified Safe" if res.get("risk_tier") == "GREEN" else "Suspicious" if res.get("risk_tier") == "AMBER" else "Critical Risk",
            final_score=res.get("final_score", 0.0) / 100.0,
            ela_score=ela.get("score", 0.0),
            metadata_score=meta.get("score", 0.0),
            seal_score=seal.get("score", 0.0),
            nlp_score=nlp.get("score", 0.0),
            ela_flags=ela.get("flags", []),
            metadata_flags=meta.get("flags", []),
            seal_flags=seal.get("flags", []),
            nlp_flags=nlp.get("flags", []),
            pattern_flags=[],
            ela_heatmap_b64=ela.get("heatmap_b64", ""),
            extracted_fields=nlp.get("entities", {}),
            registry_details={},
            llm_investigation="",
            output_dir=temp_dir,
        )
        
        pdf_path = report_res.get("pdf_path")
        html_path = report_res.get("html_path")
        
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                content = f.read()
            return Response(content=content, media_type="application/pdf")
        elif html_path and os.path.exists(html_path):
            with open(html_path, "rb") as f:
                content = f.read()
            return Response(content=content, media_type="text/html")
        else:
            raise HTTPException(status_code=500, detail="Failed to generate report files")
    except Exception as e:
        logger.error(f"[CLI Report] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------- #
#  POST /api/v1/cli/ai-summary
# --------------------------------------------------------------------------- #

class AISummaryRequest(BaseModel):
    results: dict


@router.post("/ai-summary")
async def cli_ai_summary(req: AISummaryRequest):
    """
    Stream an AI-generated forensic summary for completed scan results.
    """
    res = req.results
    filename = res.get("filename", "document")
    file_type = res.get("file_type", "PDF")
    page_count = res.get("page_count", 0)
    is_scanned = res.get("is_scanned", False)
    final_score = res.get("final_score", 0.0)
    risk_tier = res.get("risk_tier", "GREEN")

    pipelines = res.get("pipelines", {})
    ela = pipelines.get("ela", {})
    meta = pipelines.get("metadata", {})
    seal = pipelines.get("seal", {})
    nlp = pipelines.get("nlp", {})

    prompt = f"""
You are CheckMate AI, a senior forensic document investigator. Analyze the following pipeline results and write a highly professional, concise forensic summary.
Do not use emojis in your response. Keep the tone clinical, objective, and authoritative.
Limit the response to 4-5 sentences, highlighting:
1. The overall verdict and threat level.
2. The key findings from ELA, Metadata, Seal, and NLP/QR pipelines.
3. Any immediate actions recommended.

Document Details:
- Filename: {filename}
- File Type: {file_type}
- Pages: {page_count}
- Scan Status: {"Scanned" if is_scanned else "Digital PDF"}

Pipeline Metrics:
- ELA Forgery Score: {ela.get('score', 0.0)}/100 (Flags: {ela.get('flags', [])})
- Metadata Anomaly Score: {meta.get('score', 0.0)}/100 (Flags: {meta.get('flags', [])})
- Seal Tampering Score: {seal.get('score', 0.0)}/100 (Seals: {seal.get('seals_found', 0)}, Suspicious: {seal.get('suspicious', 0)}, Flags: {seal.get('flags', [])})
- NLP Semantic Score: {nlp.get('score', 0.0)}/100 (Flags: {nlp.get('flags', [])})

Global Risk Status:
- Final Integrated Score: {final_score}/100
- Risk Tier: {risk_tier}
"""

    async def event_generator():
        if settings.LLM_PROVIDER == "google":
            # Reuse the module-level singleton instead of creating a new client per request
            google_client = llm_client._get_google_client()
            from google.genai import types as genai_types
            try:
                response_stream = await google_client.aio.models.generate_content_stream(
                    model=settings.LLM_MODEL,
                    contents=[prompt],
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=settings.LLM_MAX_TOKENS,
                        temperature=settings.LLM_TEMPERATURE,
                    ),
                )
                async for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
            except Exception as e:
                logger.error("[CLI AI Summary Stream] Failed: %s", e)
                yield f"\n[Error: {e}]"
        else:
            try:
                response = await llm_client.complete(prompt)
                yield response
            except Exception as e:
                yield f"\n[Error: {e}]"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# --------------------------------------------------------------------------- #
#  GET /api/v1/cli/dashboard
# --------------------------------------------------------------------------- #

@router.get("/dashboard")
async def cli_dashboard(
    job_id: str,
    pipeline: str,
    page_num: int = 1,
    is_scanned: bool = True
):
    """
    Generate and return ELA or Seal dashboard for a scanned document page.
    """
    output_dir = Path(settings.OUTPUT_DIR) / job_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Job folder not found")

    matching_files = list(output_dir.glob(f"*_page_{page_num}.*"))
    if not matching_files:
        matching_files = list(output_dir.glob(f"*_page_{page_num}*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail=f"Page image {page_num} not found")

    img_path = str(matching_files[0].resolve())
    temp_output = Path(output_dir) / f"{pipeline}_dashboard_temp_{page_num}.png"

    try:
        if pipeline.lower() == "ela":
            import sys
            import os
            ela_dir = os.path.abspath(os.path.dirname(__file__) + "/../../pipelines/ela_forgery")
            if ela_dir not in sys.path:
                sys.path.insert(0, ela_dir)
            from backend.pipelines.ela_forgery.dashboard import build_dashboard

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                build_dashboard,
                img_path,
                str(temp_output),
                True,  # use_multiscale
                85,   # quality
                None, # preprocess
                is_scanned
            )
        elif pipeline.lower() == "seal":
            from backend.pipelines.seal_detection.visualize import generate_seal_dashboard
            from backend.pipelines.seal_detection.scorer import _detect_seals, _load_yolo_model
            
            model = _load_yolo_model()
            seal_regions = _detect_seals(img_path, model, is_scanned=is_scanned)
            
            if not seal_regions:
                raise HTTPException(status_code=400, detail="No seals detected on this page")
                
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(
                None,
                generate_seal_dashboard,
                img_path,
                seal_regions,
                str(temp_output),
                is_scanned
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to generate seal dashboard")
        else:
            raise HTTPException(status_code=400, detail="Invalid pipeline type. Choose 'ela' or 'seal'")

        if not temp_output.exists():
            raise HTTPException(status_code=500, detail="Dashboard file not generated")

        with open(temp_output, "rb") as f:
            content = f.read()

        try:
            os.remove(temp_output)
        except Exception:
            pass

        return Response(content=content, media_type="image/png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CLI Dashboard] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

