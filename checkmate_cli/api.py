"""
CheckMate CLI — HTTP API client (Python/httpx port of api.ts).

Priority for API URL: env var > ~/.checkmate/config.json > .env files > default
Priority for API key: env var > .env files
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Optional

import httpx

from checkmate_cli.config import load_config

# ── Directory resolution ─────────────────────────────────────────────────────
_CLI_DIR  = Path(__file__).parent
_ROOT_DIR = _CLI_DIR.parent          # project root (checkmate/)

DEFAULT_API_URL = "http://localhost:8000"


def _parse_env_file(env_path: Path, key: str) -> Optional[str]:
    """Extract a value from a .env file by key name."""
    try:
        text = env_path.read_text(encoding="utf-8")
        match = re.search(rf"^\s*{re.escape(key)}\s*=\s*([^\s#]+)", text, re.MULTILINE)
        if match:
            val = match.group(1).strip().strip("\"'")
            return val or None
    except Exception:
        pass
    return None


# ── Resolve API URL ──────────────────────────────────────────────────────────
def _resolve_api_url() -> str:
    url = os.environ.get("CHECKMATE_API_URL")

    if not url:
        url = load_config().get("api_url")

    if not url:
        for env_path in [_CLI_DIR / ".env", _ROOT_DIR / ".env"]:
            if env_path.exists():
                url = _parse_env_file(env_path, "CHECKMATE_API_URL")
                if url:
                    break

    url = url or DEFAULT_API_URL

    # Ensure scheme
    if not url.startswith(("http://", "https://")):
        if "localhost" in url or "127.0.0.1" in url:
            url = "http://" + url
        else:
            url = "https://" + url

    return url


# ── Resolve API key ──────────────────────────────────────────────────────────
def _resolve_api_key() -> Optional[str]:
    key = os.environ.get("CHECKMATE_API_KEY") or os.environ.get("API_KEY_SECRET")

    if not key:
        for env_path in [_CLI_DIR / ".env", _ROOT_DIR / ".env"]:
            if env_path.exists():
                key = _parse_env_file(env_path, "CHECKMATE_API_KEY") or \
                      _parse_env_file(env_path, "API_KEY_SECRET")
                if key:
                    break

    return key


API_URL = _resolve_api_url()
_API_KEY = _resolve_api_key()


def _headers(extra: dict | None = None) -> dict[str, str]:
    h: dict[str, str] = {}
    if _API_KEY:
        h["X-Api-Key"] = _API_KEY
    if extra:
        h.update(extra)
    return h


# ── Types ────────────────────────────────────────────────────────────────────
class HealthResponse:
    def __init__(self, data: dict):
        self.status      = data.get("status", "")
        self.service     = data.get("service", "")
        self.version     = data.get("version", "")
        self.db          = data.get("db", "")
        self.llm         = data.get("llm", "")
        self.environment = data.get("environment", "")


class PipelineResult:
    def __init__(self, data: dict):
        self.score = float(data.get("score", 0))
        self.flags = data.get("flags", [])
        self.raw   = data


class ScanResponse:
    def __init__(self, data: dict):
        self.filename     = data.get("filename", "")
        self.file_type    = data.get("file_type", "")
        self.page_count   = data.get("page_count", 0)
        self.is_scanned   = data.get("is_scanned", False)
        self.risk_tier    = data.get("risk_tier", "GREEN")
        self.final_score  = float(data.get("final_score", 0))
        self.pdf_metadata = data.get("pdf_metadata", {})
        self.qr_codes     = data.get("qr_codes", [])
        self.ocr_summary  = data.get("ocr_summary", "")
        self.job_id       = data.get("job_id", "")

        pipelines = data.get("pipelines", {})
        self.ela      = pipelines.get("ela", {})
        self.metadata = pipelines.get("metadata", {})
        self.seal     = pipelines.get("seal", {})
        self.nlp      = pipelines.get("nlp", {})
        # Keep raw dict for JSON serialization
        self._raw = data


# ── Health check ─────────────────────────────────────────────────────────────
async def health_check() -> Optional[HealthResponse]:
    """Ping the backend health endpoint. Returns None if unreachable."""
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            r = await client.get(f"{API_URL}/health", headers=_headers())
            if r.is_success:
                return HealthResponse(r.json())
    except Exception:
        pass
    return None


def health_check_sync() -> Optional[HealthResponse]:
    """Synchronous version of health_check for startup diagnostics."""
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get(f"{API_URL}/health", headers=_headers())
            if r.is_success:
                return HealthResponse(r.json())
    except Exception:
        pass
    return None


# ── Server launcher ──────────────────────────────────────────────────────────
def _find_uvicorn() -> str:
    """Locate the uvicorn executable inside the project venvs."""
    candidates = [
        _ROOT_DIR / ".venv"   / "Scripts" / "uvicorn.exe",
        _ROOT_DIR / "venv"    / "Scripts" / "uvicorn.exe",
        _ROOT_DIR / ".venv-1" / "Scripts" / "uvicorn.exe",
        _ROOT_DIR / ".venv"   / "bin"     / "uvicorn",
        _ROOT_DIR / "venv"    / "bin"     / "uvicorn",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return "uvicorn"


def start_server(on_progress: Callable[[str], None]) -> bool:
    """
    Start the FastAPI backend in a detached subprocess, then poll health.
    Returns True if the server becomes healthy within ~10 seconds.
    """
    on_progress("Starting FastAPI backend server...")
    uvicorn = _find_uvicorn()
    try:
        proc = subprocess.Popen(
            [uvicorn, "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(_ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for i in range(10):
            on_progress(f"Waiting for server to start... ({i + 1}/10)")
            time.sleep(1)
            h = health_check_sync()
            if h:
                on_progress("Server successfully started!")
                return True

        # If server didn't come up, clean up
        try:
            proc.terminate()
        except Exception:
            pass
    except Exception as e:
        on_progress(f"Failed to launch server process: {e}")

    return False


# ── Document scan ─────────────────────────────────────────────────────────────
def scan_document_sync(file_path: str) -> ScanResponse:
    """Upload and scan a document synchronously. Returns ScanResponse."""
    fp = Path(file_path)
    if not fp.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    with httpx.Client(timeout=120.0) as client:
        with fp.open("rb") as f:
            r = client.post(
                f"{API_URL}/api/v1/cli/scan",
                files={"file": (fp.name, f, "application/octet-stream")},
                headers=_headers(),
            )

    if not r.is_success:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(detail)

    return ScanResponse(r.json())


# ── Streaming chat ────────────────────────────────────────────────────────────
def chat_stream_sync(
    message: str,
    context: Any = None,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Yield text chunks from the Gemma chat stream (sync iterator)."""
    payload = {
        "message": message,
        "context": context,
        "history": history or [],
    }
    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            "POST",
            f"{API_URL}/api/v1/cli/chat",
            json=payload,
            headers=_headers({"Content-Type": "application/json"}),
        ) as r:
            if not r.is_success:
                raise RuntimeError(r.text)
            for chunk in r.iter_text():
                if chunk:
                    yield chunk


# ── Report generation ─────────────────────────────────────────────────────────
def generate_report_sync(results: ScanResponse) -> tuple[bytes, bool]:
    """
    Request a PDF/HTML report from the backend.
    Returns (bytes_content, is_pdf).
    """
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{API_URL}/api/v1/cli/report",
            json={"results": results._raw},
            headers=_headers({"Content-Type": "application/json"}),
        )

    if not r.is_success:
        raise RuntimeError(r.text or "Failed to generate report")

    content_type = r.headers.get("content-type", "")
    is_pdf = "pdf" in content_type
    return r.content, is_pdf


# ── AI summary ────────────────────────────────────────────────────────────────
def ai_summary_stream_sync(results: ScanResponse):
    """Yield text chunks from the AI forensic summary stream."""
    with httpx.Client(timeout=60.0) as client:
        with client.stream(
            "POST",
            f"{API_URL}/api/v1/cli/ai-summary",
            json={"results": results._raw},
            headers=_headers({"Content-Type": "application/json"}),
        ) as r:
            if not r.is_success:
                raise RuntimeError(r.text)
            for chunk in r.iter_text():
                if chunk:
                    yield chunk


# ── Dashboard generation ──────────────────────────────────────────────────────
def generate_dashboard_sync(
    job_id: str,
    pipeline: str,
    page_num: int = 1,
    is_scanned: bool = True
) -> bytes:
    """Request ELA or Seal dashboard image from the backend. Returns image bytes."""
    with httpx.Client(timeout=90.0) as client:
        r = client.get(
            f"{API_URL}/api/v1/cli/dashboard",
            params={
                "job_id": job_id,
                "pipeline": pipeline,
                "page_num": page_num,
                "is_scanned": is_scanned,
            },
            headers=_headers(),
        )

    if not r.is_success:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(detail or "Failed to generate dashboard")

    return r.content
