# chat_pipeline.py
# 42 — Chat Pipeline (polished + deterministic final cleanup)
#
# Goals:
# - Keep responses clean by default (remove common coaching preambles/tails)
# - Never crash if optional modules aren't present
# - Ensure FINAL cleanup is the *last* text mutation before returning to UI
# - Preserve your existing architecture hooks (protection, NINA, epistemic, formatter, christlike, council, voice)

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import logging
import os
import re
import uuid
from pydantic import BaseModel, Field
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger("chat_pipeline")

# -----------------------------
# Optional imports (safe)
# -----------------------------

def _safe_import(path: str, name: str, default=None):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return default

# Core response generation
generate_reply = _safe_import("reply_engine", "generate_reply", default=None)

# Ethics post-pass
christlike_response = _safe_import("ethics.ethics", "christlike_response", default=None)

# Protection guard
run_protection_guard = _safe_import("protection_pipeline", "run_protection_guard", default=None)

# NINA
analyze_nina = _safe_import("nina_pipeline", "analyze_nina", default=None)
log_nina = _safe_import("nina_pipeline", "log_nina", default=None)

# Answerability gate
answerability_gate = _safe_import("core.answerability", "answerability_gate", default=None)
Answerability = _safe_import("core.answerability", "Answerability", default=None)

# Epistemic pipeline
run_epistemic_pipeline = _safe_import("core.epistemic_pipeline", "run_epistemic_pipeline", default=None)
EpistemicFrame = _safe_import("core.epistemic_pipeline", "EpistemicFrame", default=None)

# Formatter
format_structured_response = _safe_import("core.response_formatter", "format_structured_response", default=None)

# Council agents
load_agents = _safe_import("bot_42_core.agents.agent_loader", "load_agents", default=None)

# -----------------------------
# Env flags
# -----------------------------

def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


# Default ON: keep output clean/minimal unless you explicitly turn it off.
CLEAN_CHAT_OUTPUT = _env_bool("CLEAN_CHAT_OUTPUT", "1")

# Default OFF: we don't append coaching blurbs.
CHAT_PIPELINE_COACHING = _env_bool("CHAT_PIPELINE_COACHING", "0")

# Optional speech
SPEECH_ENABLED = _env_bool("SPEECH_ENABLED", "0")
INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://127.0.0.1:8000").rstrip("/")

# -----------------------------
# In-memory conversation history
# -----------------------------

ConversationTurn = Tuple[str, str]
conversation_logs: Dict[str, List[ConversationTurn]] = defaultdict(list)

def _push_history(conv_id: str, user_text: str, assistant_text: str, max_turns: int = 20) -> None:
    try:
        conversation_logs[conv_id].append((user_text, assistant_text))
        if len(conversation_logs[conv_id]) > max_turns:
            conversation_logs[conv_id] = conversation_logs[conv_id][-max_turns:]
    except Exception:
        pass


def _history_block(conv_id: str, max_turns: int = 20) -> str:
    turns = conversation_logs.get(conv_id, [])[-max_turns:]
    if not turns:
        return ""
    # Keep it simple and stable
    return "\n".join([f"User: {u}\n42: {a}" for (u, a) in turns]).strip()


# -----------------------------
# Output cleaning (preambles/tails)
# -----------------------------

# Handles smart quotes/apostrophes and minor punctuation variants.
_PRE = [
    r"^\s*Sounds like you[’']re thinking through this carefully\.\s*",
    r"^\s*I hear you\.\s*",
    r"^\s*Got it\.\s*",
]

# Tails you explicitly want stripped.
_TAIL = [
    r"\n+\s*If you want,\s*share one constraint.*$",
    r"\n+\s*If you want,\s*give me one constraint.*$",
    r"\n+\s*I can replay that if you want\.\s*$",
]

_PREAMBLE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PRE]
_TAIL_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _TAIL]


def _clean_reply_text(reply_text: str) -> str:
    """Strip common coaching/preamble fluff from model replies."""
    if not isinstance(reply_text, str):
        return reply_text

    text = reply_text.strip()

    # Remove preambles (one pass each; keep deterministic)
    for pat in _PREAMBLE_PATTERNS:
        text = pat.sub("", text).strip()

    # Remove coaching tail(s)
    for pat in _TAIL_PATTERNS:
        text = pat.sub("", text).strip()

    return text.strip()


def _maybe_add_coaching(reply_text: str) -> str:
    """Optional coaching blurb (OFF by default)."""
    if not isinstance(reply_text, str):
        return reply_text
    if not CHAT_PIPELINE_COACHING:
        return reply_text.strip()

    # Keep it minimal
    return (reply_text.strip() + "\n\nIf you want, give me one constraint and I’ll tighten it.").strip()


def _finalize_reply_text(reply_text: str) -> str:
    """
    Final sanitation pass before returning to the UI.
    IMPORTANT: This should be the last mutation of reply text.
    """
    if not isinstance(reply_text, str):
        return reply_text

    text = reply_text.strip()

    # If coaching is enabled, add it BEFORE cleaning
    text = _maybe_add_coaching(text)

    if CLEAN_CHAT_OUTPUT:
        text = _clean_reply_text(text)

    # Normalize whitespace gently
    text = re.sub(r"[ \t]+\n", "\n", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text


# -----------------------------
# Voice helpers (safe + optional)
# -----------------------------

_last_voice_seen_id: Optional[str] = None

def _get_last_voice_meta_safe() -> Optional[dict]:
    """
    Returns last voice metadata dict or None.
    Import is inside to avoid circular-import headaches.
    """
    try:
        get_last_voice_meta = _safe_import("bot_42_core.features.api", "get_last_voice_meta", default=None)
        if get_last_voice_meta is None:
            return None
        return get_last_voice_meta()
    except Exception:
        return None


def _trigger_speech_safe(text: str) -> Optional[dict]:
    """
    Optionally triggers /speak/say with reply text.
    Returns response json (if any) else None.
    """
    if not SPEECH_ENABLED:
        return None
    if not text or not text.strip():
        return None

    try:
        import requests # local dependency; safe if installed

        r = requests.post(
            f"{INTERNAL_API_BASE}/speak/say",
            json={"text": text},
            timeout=3,
        )
        try:
            return r.json()
        except Exception:
            return {"ok": r.ok, "status_code": r.status_code, "text": (r.text or "")[:200]}
    except Exception:
        return None


def _append_voice_hint_if_new(reply_text: str) -> str:
    """
    Keep it silent by default.
    This function is here if you later want UI hints.
    """
    # Currently: do nothing (no verbosity injection)
    return reply_text


# -----------------------------
# Council (optional)
# -----------------------------

async def run_council_reasoning(user_prompt: str, importance: str = "normal") -> Tuple[str, dict]:
    """
    Run the registered agent council and return a final answer + trace.
    """
    if load_agents is None:
        return "Council is not available right now.", {"agents": [], "results": []}

    registry = load_agents()
    try:
        agent_names = registry.list_agents()
    except Exception:
        agent_names = []

    results = []
    for name in agent_names:
        try:
            agent = registry.get_agent(name)
            if agent is None:
                continue
            result = await agent.run(task=user_prompt, context={"importance": importance})
            results.append({"agent": name, "result": result})
        except Exception as e:
            results.append({"agent": name, "error": str(e)})

    # Simple combine strategy
    final = "\n\n".join(str(r.get("result", "")) for r in results if r.get("result")).strip()
    if not final:
        final = "I don’t have enough signal from the council right now."

    return final, {"agents": agent_names, "results": results}


# -----------------------------
# Pydantic models
# -----------------------------

class ChatRequest(BaseModel):
    input: str
    session_id: Optional[str] = None
    importance: Optional[str] = "normal"
    
class ChatResponse(BaseModel):
    reply: str
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())



# -----------------------------
# Wrapper: answerability gate
# -----------------------------

def handle_chat(req: ChatRequest) -> ChatResponse:
    """
    Wrapper gate in front of run_chat_pipeline.
    Keeps current behavior intact while enabling answerability routing.
    Adds session_id support for continuity.
    """
    import uuid

    user_text = (req.input or "").strip()
    session_id = (req.session_id or "").strip() or f"sess_{uuid.uuid4().hex[:12]}"

    # Developer shortcuts (optional)
    if user_text.startswith("!council:high "):
        prompt = user_text.replace("!council:high ", "", 1).strip()
        final_answer, _trace = asyncio.run(run_council_reasoning(prompt, importance="high"))
        final_answer = _finalize_reply_text(final_answer)
        return ChatResponse(reply=final_answer, session_id=session_id)

    if user_text.startswith("!council "):
        prompt = user_text.replace("!council ", "", 1).strip()
        final_answer, _trace = asyncio.run(run_council_reasoning(prompt, importance="normal"))
        final_answer = _finalize_reply_text(final_answer)
        return ChatResponse(reply=final_answer, session_id=session_id)

    # Answerability routing (if present)
    if answerability_gate is not None and Answerability is not None:
        try:
            gate = answerability_gate(user_text)
            verdict = getattr(gate, "verdict", None)

            if verdict == getattr(Answerability, "NEEDS_CLARIFICATION", None):
                qs = getattr(gate, "questions", None) or []
                q_block = "\n".join([f"- {q}" for q in qs if q]).strip()

                reply = "Can you clarify one thing for me?"
                if q_block:
                    reply += f"\n\n{q_block}"

                reply = _finalize_reply_text(reply)
                return ChatResponse(reply=reply, session_id=session_id)

            if verdict == getattr(Answerability, "REQUIRES_EXTERNAL_DATA", None):
                qs = getattr(gate, "questions", None) or []
                q_block = "\n".join([f"- {q}" for q in qs if q]).strip()

                reply = "I don’t have enough verified information to answer that reliably yet."
                if q_block:
                    reply += f"\n\nWhat would help:\n{q_block}"

                reply = _finalize_reply_text(reply)
                return ChatResponse(reply=reply, session_id=session_id)

        except Exception:
            # If gate fails, proceed normally
            pass

    # Otherwise proceed
    resp = run_chat_pipeline(user_text, session_id=session_id)

    # Support either a ChatResponse object or a plain string return
    if isinstance(resp, ChatResponse):
        # Ensure session_id always comes back
        if not getattr(resp, "session_id", None):
            resp.session_id = session_id
        final_response = resp
    else:
        final_response = ChatResponse(reply=str(resp), session_id=session_id)

    # (Answerability block runs here - now reachable)
    preflight_reply = None
    if answerability_gate is not None and Answerability is not None:
        try:
            gate = answerability_gate(user_text)
            verdict = getattr(gate, "verdict", None)

            if verdict == getattr(Answerability, "NEEDS_CLARIFICATION", None):
                qs = getattr(gate, "questions", None) or []
                q_block = "\n".join([f"- {q}" for q in qs if q]).strip()
                reply = "Can you clarify one thing for me?"
                if q_block:
                    reply += f"\n\n{q_block}"
                preflight_reply = reply

            elif verdict == getattr(Answerability, "REQUIRES_EXTERNAL_DATA", None):
                qs = getattr(gate, "questions", None) or []
                q_block = "\n".join([f"- {q}" for q in qs if q]).strip()
                reply = "I don't have enough verified information to answer that reliably yet."
                if q_block:
                    reply += f"\n\nWhat would help:\n{q_block}"
                preflight_reply = reply
        except Exception:
            pass

    if preflight_reply is not None:
        final_response.reply = preflight_reply

    return final_response

# -----------------------------
# Main pipeline
# -----------------------------

def run_chat_pipeline(user_text: str, session_id: str | None = None) -> ChatResponse:
    conv_id = session_id or "default"

    user_text = (user_text or "").strip()
    preflight_reply = None # If set, skip core LLM generation and use this reply

    # 1) Protection guard
    if run_protection_guard is not None:
        try:
            protection_result = run_protection_guard(
                user_text=user_text,
                channel="chat",
                user_id=None,
                user_role=None,
                tags=None,
            )
            if isinstance(protection_result, dict) and not protection_result.get("allowed", True):
                safe_message = protection_result.get("safe_message") or "I can’t help with that."
                safe_message = _finalize_reply_text(safe_message)
                _push_history(conv_id, user_text, safe_message)
                return ChatResponse(reply=safe_message)
        except Exception:
            # Never block if protection module throws
            pass

    # 2) NINA analysis (non-blocking)
    if analyze_nina is not None and log_nina is not None:
        try:
            nina = analyze_nina(user_text)
            _ = log_nina(user_text, nina)
        except Exception:
            pass

    # 3) Build model input with short history
    history_text = _history_block(conv_id, max_turns=20)
    if history_text:
        model_input = (
            "Recent conversation between the user and 42:\n"
            f"{history_text}\n\n"
            f"User: {user_text}"
        )
    else:
        model_input = user_text

    # 4) Epistemic pre-handler (may ask clarifying question)
    epistemic_frame = None
    if run_epistemic_pipeline is not None:
        try:
            epistemic_frame = run_epistemic_pipeline(
                model_input,
                context={
                    "conversation_id": conv_id,
                    "history_present": bool(history_text),
                },
            )
        except Exception:
            epistemic_frame = None

    # Normalize dict -> EpistemicFrame if available
    if EpistemicFrame is not None and isinstance(epistemic_frame, dict):
        try:
            epistemic_frame = EpistemicFrame(**epistemic_frame)
        except Exception:
            pass

    # Safe logging of epistemic frame
    if epistemic_frame is not None:
        try:
            if hasattr(epistemic_frame, "to_dict"):
                logger.info("epistemic_frame=%s", epistemic_frame.to_dict())
            elif isinstance(epistemic_frame, dict):
                logger.info("epistemic_frame=%s", epistemic_frame)
            else:
                logger.info("epistemic_frame=%s", str(epistemic_frame))
        except Exception:
            pass

    # Short-circuit clarifying question if epistemic says so
    try:
        needs_clar = bool(getattr(epistemic_frame, "needs_clarification", False))
        if needs_clar:
            clarifying = (
                getattr(epistemic_frame, "clarifying_question", None)
                or getattr(epistemic_frame, "clarifying_questions", None)
                or "Can you clarify what you mean?"
            )

            if isinstance(clarifying, list):
                clarifying = "\n".join([f"- {q}" for q in clarifying if q]).strip() or "Can you clarify what you mean?"

            preflight_reply = str(clarifying)
    except Exception:
        pass

    # 5) Core reply generation
    if preflight_reply is not None:
        core_reply_raw = preflight_reply
    else:
        if generate_reply is None:
            core_reply_raw = "generate_reply() is not available. Check reply_engine.py import."
        else:
            try:
                core_reply_raw = generate_reply(model_input)
            except Exception as e:
                core_reply_raw = f"Reply generation failed: {e}"
                
    # 6) Formatting layer (if available)
    if format_structured_response is not None:
        try:
            final_reply = format_structured_response(
                user_text=user_text,
                analysis=core_reply_raw,
                ask_question_if_needed=False, # epistemic already handled this
            )
        except Exception:
            final_reply = str(core_reply_raw)
    else:
        final_reply = str(core_reply_raw)

    # 7) Christ-like ethics post-pass (optional)
    if christlike_response is not None:
        try:
            final_reply = christlike_response(
                user_text=user_text,
                reply_text=final_reply,
            )
        except Exception:
            pass

    # 8) Optional speech trigger (AFTER reply is shaped)
    # Only when the user explicitly asks (you can change this trigger rule any time)
    if user_text.lower().startswith("!say "):
        _trigger_speech_safe(final_reply)

    final_reply = _append_voice_hint_if_new(final_reply)

    # ✅ 9) FINAL TEXT AUTHORITY (must be last)
    final_reply = _finalize_reply_text(final_reply)

    # 10) Update conversation memory
    _push_history(conv_id, user_text, final_reply)

    return ChatResponse(reply=final_reply, session_id=conv_id)


__all__ = [
    "ChatRequest",
    "ChatResponse",
    "handle_chat",
    "run_chat_pipeline",
]