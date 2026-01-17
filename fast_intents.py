# fast_intents.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import os
import time


# -------------------------
# Runtime state
# -------------------------

_APP_START_TS = time.time()


def _uptime_parts() -> tuple[int, int, int]:
    uptime_s = max(0, int(time.time() - _APP_START_TS))
    hh = uptime_s // 3600
    mm = (uptime_s % 3600) // 60
    ss = uptime_s % 60
    return hh, mm, ss


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repl_id() -> str:
    return os.getenv("REPL_ID") or os.getenv("REPL_SLUG") or "unknown"


def _runtime() -> str:
    return os.getenv("RUNTIME", "replit")


def _app_version() -> str:
    return os.getenv("APP_VERSION", "dev")


def _bind_hint() -> str:
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    return f"{host}:{port}"


# -------------------------
# Renderers
# -------------------------

def build_status_lines() -> list[str]:
    hh, mm, ss = _uptime_parts()
    return [
        "42 STATUS ✅",
        f"time_utc: {_now_utc_iso()}",
        f"uptime: {hh:02d}h {mm:02d}m {ss:02d}s",
        f"app_version: {_app_version()}",
        f"runtime: {_runtime()}",
        f"repl: {_repl_id()}",
        f"bind: {_bind_hint()}",
    ]


def build_help_lines() -> list[str]:
    return [
        "42 HELP ✅",
        "Commands:",
        "- status (or /status) -> runtime status",
        "- version (or /version) -> app version",
        "- whoami (or /whoami) -> identity/runtime info",
        "- help (or /help, or ?) -> this help",
        "",
        "API endpoints:",
        "- GET /health",
        "- GET /status",
        "- GET /version",
        "- GET /whoami",
        "- POST /chat",
        "- POST /chat/council",
    ]


def build_whoami_lines() -> list[str]:
    # NOTE: This is a *safe* conversational whoami.
    # It intentionally does NOT inspect request headers or IPs.
    hh, mm, ss = _uptime_parts()
    return [
        "42 WHOAMI ✅",
        f"app_version: {_app_version()}",
        f"runtime: {_runtime()}",
        f"repl: {_repl_id()}",
        f"bind: {_bind_hint()}",
        f"uptime: {hh:02d}h {mm:02d}m {ss:02d}s",
        f"time_utc: {_now_utc_iso()}",
    ]


# -------------------------
# Fast intent router (NO LLM)
# -------------------------

def fast_intent_reply(user_text: str) -> Optional[str]:
    raw = (user_text or "").strip()
    if not raw:
        return None

    cmd = raw.lower()

    if cmd in ("status", "/status"):
        return "\n".join(build_status_lines())

    if cmd in ("help", "/help", "?"):
        return "\n".join(build_help_lines())

    if cmd in ("version", "/version"):
        return f"42 VERSION ✅\n{_app_version()}"

    if cmd in ("whoami", "/whoami"):
        return "\n".join(build_whoami_lines())

    return None