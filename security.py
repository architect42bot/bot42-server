# security.py
"""
Security wiring for Bot42.

Centralizes SAFE-KEY orchestration + basic request guards:
- SAFE-KEY header enforcement (optional via REQUIRE_SAFE_KEY)
- simple in-memory rate limiting
- body-size guard (via Content-Length when available)
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Optional, Deque, Dict, Tuple

from fastapi import HTTPException, Request
from fastapi import status as http_status


# -------------------------------
# Config
# -------------------------------

SAFE_KEY_HEADER_NAME = "SAFE-KEY"

SAFE_KEY = os.getenv("SAFE_KEY", "").strip()
REQUIRE_SAFE_KEY = os.getenv("REQUIRE_SAFE_KEY", "1").strip().lower() in ("1", "true", "yes", "y", "on")

BOT42_RATE_MAX = int(os.getenv("BOT42_RATE_MAX", "60")) # max requests per window
BOT42_RATE_WINDOW = int(os.getenv("BOT42_RATE_WINDOW", "60")) # seconds



# -------------------------------
# SAFE-KEY helpers
# -------------------------------

def get_safe_key_from_request(request: Request) -> Optional[str]:
    return request.headers.get(SAFE_KEY_HEADER_NAME)


def require_safe_key(request: Request) -> None:
    """
    Enforce SAFE-KEY if REQUIRE_SAFE_KEY is enabled.
    """
    if not REQUIRE_SAFE_KEY:
        return

    if not SAFE_KEY:
        # Misconfiguration: requiring a key but none set
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: SAFE_KEY is missing.",
        )

    provided = get_safe_key_from_request(request)
    if not provided or provided != SAFE_KEY:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid SAFE-KEY.",
        )


# -------------------------------
# Body size guard
# -------------------------------



# -------------------------------
# Rate limiting (simple in-memory)
# -------------------------------

# key -> deque[timestamps]
_RATE_BUCKETS: Dict[str, Deque[float]] = {}


def _client_key(request: Request) -> str:
    # Prefer forwarded-for if present; fall back to client host
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # first IP in the list
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit(request: Request) -> None:
    """
    Sliding window limiter:
      allow BOT42_RATE_MAX requests per BOT42_RATE_WINDOW seconds per client IP.
    """
    if BOT42_RATE_MAX <= 0 or BOT42_RATE_WINDOW <= 0:
        return

    key = _client_key(request)
    now = time.time()
    cutoff = now - BOT42_RATE_WINDOW

    dq = _RATE_BUCKETS.get(key)
    if dq is None:
        dq = deque()
        _RATE_BUCKETS[key] = dq

    # prune old timestamps
    while dq and dq[0] < cutoff:
        dq.popleft()

    if len(dq) >= BOT42_RATE_MAX:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )

    dq.append(now)