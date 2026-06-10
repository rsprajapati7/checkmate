"""
CheckMate / Suraksha 2.0 — FastAPI Application Entry Point

Startup hooks:
  - Initialize DB tables
  - Preload YOLO model (avoid cold-start latency on first request)
  - LLM connectivity ping

Routes:
  POST /api/v1/documents/upload       → upload + trigger pipeline
  POST /api/v1/documents/{id}/analyze → re-trigger analysis
  GET  /api/v1/jobs/{job_id}          → poll status
  GET  /api/v1/reports/{job_id}       → get JSON report
  GET  /api/v1/reports/{job_id}/pdf   → download PDF
  GET  /health                        → health check
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import upload, analyze, status, report, cli_routes
from backend.core.config import settings
from backend.core.database import init_db, ping_db
from backend.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("=== CheckMate / Suraksha 2.0 Starting ===")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER} / Model: {settings.LLM_MODEL}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"DB init failed: {e}")

    # LLM ping (non-blocking warning)
    try:
        from backend.ai_investigator.llm_client import llm_client
        ok = await llm_client.ping()
        if ok:
            logger.info(f"LLM ({settings.LLM_PROVIDER}/{settings.LLM_MODEL}) — reachable.")
        else:
            logger.warning(f"LLM ({settings.LLM_PROVIDER}/{settings.LLM_MODEL}) — not reachable. Check API key / Ollama.")
    except Exception as e:
        logger.warning(f"LLM ping failed: {e}")

    yield

    logger.info("=== CheckMate Shutting Down ===")


app = FastAPI(
    title="CheckMate Forensic API",
    description="Suraksha 2.0 — AI-powered document forgery detection",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(status.router)
app.include_router(report.router)
app.include_router(cli_routes.router)


_llm_ok_cache = {"status": False, "timestamp": 0.0}


@app.get("/health", tags=["system"])
async def health_check():
    """Extended health check — DB, LLM, model status."""
    import time
    import asyncio

    db_ok = await ping_db()
    
    now = time.time()
    # Cache health check for 60 seconds to avoid hitting API rate limits and causing startup timeouts
    if now - _llm_ok_cache["timestamp"] > 60.0:
        llm_ok = False
        try:
            from backend.ai_investigator.llm_client import llm_client
            llm_ok = await asyncio.wait_for(llm_client.ping(), timeout=5.0)
        except Exception:
            pass
        _llm_ok_cache["status"] = llm_ok
        _llm_ok_cache["timestamp"] = now

    llm_ok = _llm_ok_cache["status"]

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "checkmate",
        "version": "2.0.0",
        "db": "connected" if db_ok else "disconnected",
        "llm": f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL} — {'ok' if llm_ok else 'unreachable'}",
        "environment": settings.ENVIRONMENT,
    }
