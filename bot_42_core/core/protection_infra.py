"""
bot_42_core/core/protection_infra.py

Central request protection utilities:
- SAFE-KEY header enforcement
- Body size caps (prevents giant payload abuse)
- Text length caps (prevents runaway prompts)

This is designed to be used as FastAPI dependencies, e.g.:

from bot_42_core.core.protection_infra import protected_dependency

@app.post("/protected/chat", dependencies=[Depends(protected_dependency)])
async def chat(...):
    ...

or:

async def chat(dep: None = Depends(protected_dependency)):
    ...
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, Request, status


# -------------------------
# Config helpers
# -------------------------

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _expected_safe_key() -> Optional[str]:
    """
    Where we read the expected key from.

    Use whichever you prefer; both are supported:
      - BOT42_SAFE_KEY (preferred)
      - SAFE_KEY (fallback)
    """
    return os.getenv("BOT42_SAFE_KEY") or os.getenv("SAFE_KEY")


# Defaults are conservative + practical for your use case
DEFAULT_MAX_BODY_BYTES = _env_int("BOT42_MAX_BODY_BYTES", 256_000)      # ~256KB
DEFAULT_MAX_TEXT_CHARS = _env_int("BOT42_MAX_TEXT_CHARS", 8_000)        # prompt-size cap


# -------------------------
# SAFE-KEY enforcement
# -------------------------

async def enforce_safe_api_key(safe_key: Optional[str] = None) -> None:
    """
    Enforce SAFE-KEY presence and validity.

    FastAPI will inject the header value into `safe_key` (via Header(alias="SAFE-KEY"))
    when used in a dependency function.
    """
    expected = _expected_safe_key()

    # If you haven't configured an expected key, we treat that as misconfiguration
    # and fail closed for protected endpoints.
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server SAFE-KEY is not configured (set BOT42_SAFE_KEY).",
        )

    if not safe_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing SAFE-KEY header",
        )

    if safe_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid SAFE-KEY",
        )


# -------------------------
# Body size protection
# -------------------------

async def check_body_size(request: Request, max_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
    """
    Enforce maximum request body size.

    NOTE: calling request.body() reads and caches the body, so downstream handlers
    can still access it without re-reading the stream.
    """
    try:
        body = await request.body()
    except Exception:
        # If body can't be read, treat as bad request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read request body",
        )

    if body is None:
        return

    if len(body) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body too large. Max allowed is {max_bytes} bytes.",
        )


# -------------------------
# Text-length protection
# -------------------------

def enforce_text_length(text: str, max_chars: int = DEFAULT_MAX_TEXT_CHARS) -> None:
    """
    Enforce maximum characters for a text field you plan to send to an LLM/TTS/etc.
    Call this inside endpoints where you accept user 'message', 'text', etc.
    """
    if not isinstance(text, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text must be a string",
        )

    if len(text) > max_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Input text too long. Max allowed is {max_chars} characters.",
        )


# -------------------------
# Composite dependency (what you use on routes)
# -------------------------

async def protected_dependency(
    request: Request,
    safe_key: Optional[str] = Header(default=None, alias="SAFE-KEY"),
) -> None:
    """
    Composite dependency for protected routes.

    - Verifies SAFE-KEY header
    - Enforces request body size limits
    """

    raw = (
        safe_key
        or request.headers.get("SAFE-KEY")
        or request.headers.get("safe-key")
        or request.headers.get("X-SAFE-KEY")
        or request.headers.get("x-safe-key")
    )

    await enforce_safe_api_key(raw)
    await check_body_size(request)