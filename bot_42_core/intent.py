# bot_42_core/intent.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IntentResult:
    intent: str # e.g. "chat", "help", "status", "tool", "memory", "unknown"
    confidence: float # 0.0 - 1.0
    reason: str # short explanation for logs/debug
    tool_name: Optional[str] = None


def classify_intent(user_text: str) -> IntentResult:
    """
    Lightweight, deterministic intent classification.
    This runs BEFORE any LLM call.
    Keep it simple: keywords + basic heuristics.
    """
    t = (user_text or "").strip().lower()
    if not t:
        return IntentResult("empty", 1.0, "no user_text")

    # quick "help" / meta
    if t in {"help", "/help", "?"} or "what can you do" in t:
        return IntentResult("help", 0.95, "help request")

    # quick status / health-ish
    if "status" in t or "are you online" in t or "uptime" in t:
        return IntentResult("status", 0.75, "status-like request")

    # explicit tool-ish cues (expand later)
    tool_triggers = ("search", "lookup", "open ", "summarize", "translate", "calculate")
    if any(t.startswith(x) for x in tool_triggers):
        return IntentResult("tool", 0.70, "tool trigger word at start")

    # explicit memory-ish cues (expand later)
    if t.startswith("remember ") or "save this" in t or "forget " in t:
        return IntentResult("memory", 0.80, "explicit memory directive")

    # default: normal chat
    return IntentResult("chat", 0.60, "default to chat")