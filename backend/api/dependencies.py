import hmac

from fastapi import Header, HTTPException

from backend.core.config import settings


from typing import Optional

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """
    Validate the X-Api-Key header against the configured secret.

    Uses hmac.compare_digest to prevent timing-side-channel attacks.
    Raises HTTP 403 if the key is missing or does not match.
    """
    if not settings.API_KEY_SECRET:
        # In development with no key configured, skip auth
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.API_KEY_SECRET):
        raise HTTPException(status_code=403, detail="Invalid API key")
