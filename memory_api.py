# memory_api.py
# Lightweight API shim over memory_store.py with optional reflection support.

from __future__ import annotations
from typing import List, Dict, Any

# --- Core memory functions (from your function-based memory_store.py) ---
from memory_store import (
    log_user as _store_log_user,
    log_assistant as _store_log_assistant,
    recall as _store_recall,
    top_facts as _store_top_facts,
    recent_summaries as _store_recent_summaries,
)

# --- Optional reflection support (safe no-op if not available) ---
_reflector = None
_maybe_reflect_fn = None
try:
    # Support either a Reflector class with maybe_reflect(), or a free function maybe_reflect()
    from reflection import Reflector  # type: ignore
    try:
        _reflector = Reflector()  # allow default constructor
    except Exception:
        _reflector = None
except Exception:
    pass

try:
    from reflection import maybe_reflect as _maybe_reflect_fn  # type: ignore
except Exception:
    _maybe_reflect_fn = None


def _reflect_safe() -> Dict[str, Any]:
    """Try to run a reflection step; never raise."""
    try:
        if _maybe_reflect_fn:
            return _maybe_reflect_fn()  # type: ignore[misc]
        if _reflector and hasattr(_reflector, "maybe_reflect"):
            return _reflector.maybe_reflect()  # type: ignore[call-arg]
    except Exception as e:
        return {"reflected": False, "error": str(e)}
    return {"reflected": False, "reason": "no reflector available"}


# ---------------- Public API (stable signatures) ----------------

def log_user(text: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Record a user message; meta accepted for compatibility (ignored by store)."""
    rec = _store_log_user(text)
    _reflect_safe()
    return rec

def log_assistant(text: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Record an assistant message; meta accepted for compatibility (ignored by store)."""
    rec = _store_log_assistant(text)
    _reflect_safe()
    return rec

def recall(query: str, k: int = 5) -> List[Dict[str, Any]]:
    return _store_recall(query, k=k)

def top_facts(k: int = 10) -> List[str]:
    return _store_top_facts(k=k)

def recent_summaries(k: int = 5) -> List[str]:
    return _store_recent_summaries(k=k)