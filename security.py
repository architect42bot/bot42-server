# security.py
"""
Security wiring for Bot42.

NOTE:
- No new logic.
- This module only centralizes SAFE-KEY related orchestration.
"""

from typing import Optional
from fastapi import Request

# Canonical header name
SAFE_KEY_HEADER_NAME = "SAFE-KEY"


def get_safe_key_from_request(request: Request) -> Optional[str]:
    """
    Extract SAFE-KEY from request headers.
    Mirrors existing behavior in main.py.
    """
    return request.headers.get(SAFE_KEY_HEADER_NAME)