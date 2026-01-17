# bot_42_core/llm_core.py
from __future__ import annotations

import os
import time
from datetime import datetime,timezone
from typing import Any, Optional

from openai import OpenAI

from bot_42_core.intent import classify_intent

# IMPORTANT: we now import the public function name
from bot_42_core.prompt_builder import build_system_prompt

_START_TIME = time.time()

def build_status_reply() -> str:
    now = datetime.now(timezone.utc).isoformat()
    uptime_s = int(time.time() - _START_TIME)

    version = os.getenv("APP_VERSION", "dev")

    return (
        "✅ 42 status: ONLINE\n"
        f"Version: {version}\n"
        f"Uptime: {uptime_s}s\n"
        f"Time (UTC): {now}"
    )

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini") # change if you want
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "512"))

def _fmt_uptime(seconds: float) -> str:
    seconds = int(max(0, seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02}h {minutes:02}m {secs:02}s"
    return f"{hours:02}h {minutes:02}m {secs:02}s"


def build_status_reply(session_id: Optional[str] = None) -> str:
    now_utc = datetime.now(timezone.utc)
    uptime = _fmt_uptime(time.time() - _START_TIME)

    # Keep this lightweight + safe (no secrets)
    app_version = os.getenv("APP_VERSION", "dev")
    repl_slug = os.getenv("REPL_SLUG") or os.getenv("REPLIT_DB_URL", None) # optional hint
    repl_hint = "replit" if repl_slug else "unknown"

    lines = [
        "42 STATUS ✅",
        f"- time_utc: {now_utc.isoformat().replace('+00:00', 'Z')}",
        f"- uptime: {uptime}",
        f"- app_version: {app_version}",
        f"- model: {MODEL_NAME}",
        f"- max_output_tokens: {MAX_OUTPUT_TOKENS}",
        f"- runtime: {repl_hint}",
    ]
    if session_id:
        lines.append(f"- session_id: {session_id}")

    return "\n".join(lines)

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _extract_output_text(response: Any) -> str:
    """
    Works with Responses API objects.
    """
    # New SDK convenience
    txt = getattr(response, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

    # Fallback: attempt to walk structured output
    out = getattr(response, "output", None)
    if isinstance(out, list):
        chunks = []
        for item in out:
            content = getattr(item, "content", None)
            if isinstance(content, list):
                for c in content:
                    t = getattr(c, "text", None)
                    if isinstance(t, str):
                        chunks.append(t)
        joined = "\n".join(x for x in chunks if x.strip()).strip()
        if joined:
            return joined

    return ""


def generate_llm_reply(
    
    user_text: str,
    session_id: Optional[str] = None,
    tone: str = "balanced",
    nina: Any = None,
    ethics: Any = None,
) -> str:
    """
    Core LLM function used by your /chat endpoint.
    Always returns a string (never throws upstream).
    """

    print(">>> llm_core.generate_llm_reply HIT <<<", repr(user_text), flush=True)
    print(">>> llm_core file:", __file__, flush=True)

    try:
        if not user_text or not user_text.strip():
            return "Could you tell me a little more?"

        user_text = user_text.strip()
        lower = user_text.lower()

        if lower in ("status", "/status"):
            from datetime import datetime, timezone
            import os, time

            now_utc = datetime.now(timezone.utc)
            uptime_s = int(time.time() - _START_TIME)
            hh = uptime_s // 3600
            mm = (uptime_s % 3600) // 60
            ss = uptime_s % 60

            app_version = os.getenv("APP_VERSION", "dev")
            runtime = os.getenv("RUNTIME", "replit")
            repl_id = os.getenv("REPL_ID") or os.getenv("REPL_SLUG")
            host = os.getenv("HOST", "")
            port = os.getenv("PORT", "")

            lines = [
                "42 STATUS ✅",
                f"time_utc: {now_utc.isoformat()}",
                f"uptime: {hh:02d}h {mm:02d}m {ss:02d}s",
                f"app_version: {app_version}",
                f"model: {MODEL_NAME}",
                f"max_output_tokens: {MAX_OUTPUT_TOKENS}",
                f"runtime: {runtime}",
                f"session_id: {session_id or 'none'}",
                f"repl: {repl_id or 'unknown'}",
                f"bind: {host or '0.0.0.0'}:{port or '8000'}",
            ]
            return "\n".join(lines)
        
        # ---- Normal LLM flow ----
        system_prompt = build_system_prompt(user_msg=user_text, tone=tone, nina=nina, ethics=ethics)

        model = MODEL_NAME
        print(f"[llm_core] Using model: {model}")
        if session_id:
            print(f"[llm_core] session_id={session_id}")

        client = _get_client()

        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        reply_text = _extract_output_text(response).strip()
        if not reply_text:
            print("[llm_core] Empty reply_text from model")
            return "I'm having trouble forming a reply right now. Please try again in a moment."

        print(f"[llm_core] returning reply of length {len(reply_text)}")
        return reply_text

    except Exception as exc:
        # NOTHING escapes this function; caller always gets a string.
        print(f"[llm_core] FATAL error in generate_llm_reply: {exc!r}")
        return "I'm having a temporary problem reaching my LLM core. Could you try that again in a moment?"
