from typing import Optional
import os

from fastapi import Header, HTTPException, Request, status

# -------------------------------------------------------------------
# Shared SAFE_KEY config
# -------------------------------------------------------------------

SAFE_KEY = os.getenv("SAFE_KEY")


# -------------------------------------------------------------------
# API key guard (header: SAFE-KEY)
# -------------------------------------------------------------------

async def enforce_safe_api_key(
    safe_key: Optional[str] = Header(default=None, alias="SAFE-KEY"),
) -> None:
    """
    Unified API-key guard for protected endpoints.

    - Reads SAFE_KEY from the environment.
    - Expects clients to send:  SAFE-KEY: <SAFE_KEY>  in headers.
    """

    if SAFE_KEY is None:
        # Server misconfiguration – key not set
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAFE_KEY not configured on server",
        )

    if not safe_key or safe_key != SAFE_KEY:
        # Missing or wrong key
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


# -------------------------------------------------------------------
# Request size guard
# -------------------------------------------------------------------

async def check_body_size(
    request: Request,
    max_bytes: int = 32_000,
) -> None:
    """
    Lightweight body-size guard based on the Content-Length header.
    """
    content_length = request.headers.get("content-length")

    # If client didn't send Content-Length, just skip this check.
    if content_length is None:
        return

    try:
        size = int(content_length)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Content-Length header",
        )

    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request body too large. Max allowed is {max_bytes} bytes.",
        )


# -------------------------------------------------------------------
# Text-length guard for JSON chat-style payloads
# -------------------------------------------------------------------

async def ensure_text_length(
    request: Request,
    max_chars: int = 16_000,
) -> None:
    """
    Guard to keep text inputs from being absurdly large.

    Assumes JSON body with one of:
      - "input"
      - "text"
      - "message"
    """
    if request.method not in {"POST", "PUT", "PATCH"}:
        return

    try:
        body = await request.json()
    except Exception:
        # If it's not JSON, just skip – other layers will complain if needed.
        return

    text = (
        (body.get("input") or body.get("text") or body.get("message") or "")
        if isinstance(body, dict)
        else ""
    )

    if not isinstance(text, str):
        return

    if len(text) > max_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Input text too long. Max allowed is {max_chars} characters.",
        )


# -------------------------------------------------------------------
# Combined dependency used by main.py
# -------------------------------------------------------------------

async def protected_dependency(
    request: Request,
    safe_key: Optional[str] = Header(default=None, alias="SAFE-KEY"),
) -> None:
    """
    Composite dependency for sensitive endpoints.

    - Verifies SAFE-KEY header.
    - Checks overall request body size.
    """
    await enforce_safe_api_key(safe_key=safe_key)
    await check_body_size(request)
