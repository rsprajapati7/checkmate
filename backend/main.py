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

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.api.dependencies import verify_api_key
from backend.api.routes import upload, analyze, status, report, cli_routes
from backend.core.config import settings
from backend.core.database import init_db, ping_db
from backend.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("=== CheckMate / Suraksha 2.0 Starting ===")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("LLM Provider: %s / Model: %s", settings.LLM_PROVIDER, settings.LLM_MODEL)

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error("DB init failed: %s", e)

    # LLM ping (non-blocking warning)
    try:
        from backend.ai_investigator.llm_client import llm_client
        ok = await llm_client.ping()
        if ok:
            logger.info("LLM (%s/%s) — reachable.", settings.LLM_PROVIDER, settings.LLM_MODEL)
        else:
            logger.warning(
                "LLM (%s/%s) — not reachable. Check API key / Ollama.",
                settings.LLM_PROVIDER, settings.LLM_MODEL,
            )
    except Exception as e:
        logger.warning("LLM ping failed: %s", e)

    yield

    logger.info("=== CheckMate Shutting Down ===")


app = FastAPI(
    title="CheckMate Forensic API",
    description="Suraksha 2.0 — AI-powered document forgery detection",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — restrict origins based on environment (CRITICAL-01 fix)
# ---------------------------------------------------------------------------
if settings.ENVIRONMENT == "production":
    _cors_origins = [settings.FRONTEND_URL]
else:
    # Development: allow localhost on common ports
    _cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Process-time header middleware (MEDIUM-23 fix — was defined but never used)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
    return response


# Register routers
app.include_router(upload.router, dependencies=[Depends(verify_api_key)])
app.include_router(analyze.router, dependencies=[Depends(verify_api_key)])
app.include_router(status.router, dependencies=[Depends(verify_api_key)])
app.include_router(report.router, dependencies=[Depends(verify_api_key)])
app.include_router(cli_routes.router, dependencies=[Depends(verify_api_key)])


_llm_ok_cache = {"status": False, "timestamp": 0.0}


@app.get("/health", tags=["system"])
async def health_check():
    """Extended health check — DB, LLM, model status."""
    import asyncio

    db_ok = await ping_db()

    now = time.time()
    # Cache health check for 60 seconds to avoid hitting API rate limits
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


@app.get("/health/live", tags=["system"])
async def liveness():
    """K8s liveness probe — returns 200 if process is alive."""
    return {"alive": True}


@app.get("/health/ready", tags=["system"])
async def readiness():
    """K8s readiness probe — returns 200 only when DB is connected."""
    db_ok = await ping_db()
    if not db_ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not ready")
    return {"ready": True}
