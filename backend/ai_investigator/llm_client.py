"""
Unified LLM client for Gemma 4 31B via Google AI Studio API.

Supports dual-mode:
  - "google" : gemma-4-31b-it via google-generativeai SDK (AI Studio)
  - "ollama" : local Ollama inference (fallback for offline dev)
"""

import asyncio
import json
import re
from typing import Any, Optional

import httpx

from backend.core.config import settings
from backend.core.exceptions import LLMError
from backend.core.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self._google_client = None

    def _get_google_client(self):
        if self._google_client is None:
            try:
                from google import genai
                self._google_client = genai.Client(api_key=settings.GEMMA_API_KEY)
            except ImportError:
                raise LLMError("google-genai not installed. Run: pip install google-genai")
            except Exception as e:
                raise LLMError(f"Failed to initialize Google GenAI client: {e}")
        return self._google_client

    async def complete(self, prompt: str, image_b64: Optional[str] = None) -> str:
        """Send a text (and optionally image) prompt, return the response string."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._complete_sync, prompt, image_b64)

    def _complete_sync(self, prompt: str, image_b64: Optional[str]) -> str:
        if self.provider == "google":
            return self._google_complete(prompt, image_b64)
        else:
            return self._ollama_complete(prompt)

    def _google_complete(self, prompt: str, image_b64: Optional[str]) -> str:
        """Call Gemma 4 31B via Google AI Studio (google.genai SDK)."""
        from google import genai
        from google.genai import types

        client = self._get_google_client()
        contents = []

        if image_b64:
            import base64
            contents.append(types.Part.from_bytes(
                data=base64.b64decode(image_b64),
                mime_type="image/png",
            ))

        contents.append(prompt)

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                    temperature=settings.LLM_TEMPERATURE,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"[LLM] Google API error: {e}")
            raise LLMError(f"Google GenAI call failed: {e}") from e

    def _ollama_complete(self, prompt: str) -> str:
        """Call local Ollama API."""
        url = f"{settings.OLLAMA_API_BASE}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": settings.LLM_TEMPERATURE,
                "num_predict": settings.LLM_MAX_TOKENS,
            }
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"[LLM] Ollama error: {e}")
            raise LLMError(f"Ollama call failed: {e}") from e

    async def complete_json(self, prompt: str, image_b64: Optional[str] = None) -> dict:
        """
        Same as complete() but expects JSON response.
        Attempts to parse JSON from the model output, with fallback extraction.
        """
        raw = await self.complete(prompt, image_b64)
        return _extract_json(raw)

    async def ping(self) -> bool:
        """Health check — returns True if LLM is reachable."""
        try:
            resp = await self.complete("Reply with only: ok")
            return bool(resp.strip())
        except Exception:
            return False


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response that may have markdown code fences."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding the first { ... } object
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(f"[LLM] Could not extract JSON from response: {text[:300]}")
    return {"error": "json_parse_failed", "raw": text[:500]}


# Singleton instance
llm_client = LLMClient()
