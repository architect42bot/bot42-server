# protection_pipeline.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ProtectionTestRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    channel: Optional[str] = None
    tags: Optional[List[str]] = None


def run_protection_guard(
    user_text: str,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    channel: str = "chat",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Core protection / policy guard used by /safe (and later chat routes).

    Returns a stable JSON dict:
      {
        "allowed": bool,
        "reason": str,
        "ethics": {...},
        "context": {...}
      }
    """
    text = (user_text or "").strip()

    # --- Christ-ethics evaluation ---
    # NOTE: run_christ_ethic is expected to exist in main.py in your project today.
    # We import lazily here to avoid circular imports.
    try:
        from main import run_christ_ethic # type: ignore
    except Exception as e:
        # Fail-safe: if ethics function cannot be imported, block with diagnostics.
        return {
            "allowed": False,
            "reason": "ethics_import_error",
            "error": str(e),
            "ethics": {
                "score": -1.0,
                "confidence": 0.0,
                "notes": {
                    "epistemic_level": "CERTAIN",
                    "principles_applied": ["fail_safe"],
                    "flags": ["ethics_import_error"],
                    "detail": "Could not import run_christ_ethic from main.py",
                },
            },
            "context": {
                "channel": channel,
                "user_id": user_id,
                "user_role": user_role,
                "tags": tags,
            },
        }

    christ_eval = run_christ_ethic(text)

    # Decision rule (tune later):
    # score is in [-1, 1]. Block if strongly negative.
    allowed = float(christ_eval.get("score", -1.0)) >= -0.5

    return {
        "allowed": allowed,
        "reason": "christ_ethic",
        "ethics": christ_eval,
        "context": {
            "channel": channel,
            "user_id": user_id,
            "user_role": user_role,
            "tags": tags,
        },
    }