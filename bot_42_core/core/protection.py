# bot_42_core/core/protection.py

"""
protection.py

Core protection logic for 42.

Goal:
- Protect the innocent.
- Avoid helping with harm.
- Stay aligned with Christ-like ethics (compassion, truth, mercy, justice).
- Be easy to plug into the rest of the system without importing half the codebase.

This module is intentionally self-contained:
- It does NOT import other 42 modules (ethics, nina, etc.).
- It only uses the standard library and typing.
- Other parts of the system can call into it as a pure utility layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------


class ProtectionLevel(str, Enum):
    """How strong the protection response should be."""
    ALLOW = "allow"       # allow as-is
    WARN = "warn"         # allow but with a gentle warning
    BLOCK = "block"       # refuse / stop
    ESCALATE = "escalate" # log / escalate for further review


@dataclass
class ProtectionContext:
    """
    Context about the request, as seen by 42.

    Nothing here is required at runtime; everything is optional so
    other parts of the system can pass only what they know.
    """

    user_id: Optional[str] = None
    user_role: Optional[str] = None   # "adult", "minor", "staff", etc.
    channel: Optional[str] = None     # "cli", "api", "web", etc.
    source_ip: Optional[str] = None

    # High-level tags the caller can attach, if known.
    tags: Optional[List[str]] = None  # e.g. ["self-harm-risk", "violence"]


@dataclass
class ProtectionDecision:
    """
    Result of evaluating a piece of content / request.

    The rest of the system should be able to look at:
    - level: What should 42 do?
    - reasons: Why did 42 decide this?
    - notes: Extra metadata for logs, dashboards, etc.
    """

    level: ProtectionLevel
    reasons: List[str]
    notes: Dict[str, Any]

    def is_allowed(self) -> bool:
        """Convenience helper: True if the request is not blocked."""
        return self.level in (ProtectionLevel.ALLOW, ProtectionLevel.WARN)


# ---------------------------------------------------------------------------
# Simple rule helpers
# ---------------------------------------------------------------------------


def looks_like_minor(context: Optional[ProtectionContext]) -> bool:
    """
    Very rough heuristic to decide if the user might be a minor.

    This is intentionally simple and conservative. If we're not sure, we
    don't assume minor; we just fall back to content-only signals.
    """
    if context is None:
        return False

    if context.user_role and context.user_role.lower() in {"minor", "child", "teen"}:
        return True

    if context.tags and any(t.lower() in {"minor", "underage"} for t in context.tags):
        return True

    return False


def _contains_violence(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "kill",
        "murder",
        "stab",
        "shoot",
        "blow up",
        "assassinate",
        "torture",
        "bomb",
        "massacre",
        "wipe them out",
        "race war",
    ]
    return any(k in lowered for k in keywords)


def _contains_self_harm(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "kill myself",
        "suicide",
        "end my life",
        "self harm",
        "cut myself",
        "hurt myself on purpose",
        "i want to die",
        "i wish i was dead",
    ]
    return any(k in lowered for k in keywords)


def _contains_sexual_exploit(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "underage",
        "minor",
        "child porn",
        "cp",
        "13 year old",
        "14 year old",
        "15 year old",
    ]
    return any(k in lowered for k in keywords)


def _contains_hate_or_targeting(text: str) -> bool:
    lowered = text.lower()
    keywords = [
        "genocide",
        "ethnic cleansing",
        "exterminate them",
        "wipe them out",
        "race war",
    ]
    return any(k in lowered for k in keywords)


# ---------------------------------------------------------------------------
# Main decision function
# ---------------------------------------------------------------------------


def evaluate_protection(
    user_text: str,
    context: Optional[ProtectionContext] = None,
) -> ProtectionDecision:
    """
    Main entry point.

    Given user_text (what the user is asking/saying) and optional context,
    return a ProtectionDecision about how 42 should respond.

    This is intentionally simple and transparent; it can be expanded later
    or wired into more advanced ethics/NINA logic.
    """
    reasons: List[str] = []
    notes: Dict[str, Any] = {
        "version": "v1",
        "has_context": context is not None,
    }

    # Base assumption
    level = ProtectionLevel.ALLOW

    # 1) Self-harm
    if _contains_self_harm(user_text):
        level = ProtectionLevel.BLOCK
        reasons.append("Detected self-harm or suicidal language.")
        notes["category"] = "self_harm"
        # In a Christ-like framework, this is where you pivot to care + support.
        return ProtectionDecision(level=level, reasons=reasons, notes=notes)

    # 2) Violence / violent instructions
    if _contains_violence(user_text):
        level = ProtectionLevel.BLOCK
        reasons.append("Detected violent or lethal intent.")
        notes["category"] = "violence"
        return ProtectionDecision(level=level, reasons=reasons, notes=notes)

    # 3) Sexual exploitation / minors
    if _contains_sexual_exploit(user_text) or looks_like_minor(context):
        level = ProtectionLevel.BLOCK
        reasons.append("Detected content related to minors / exploitation.")
        notes["category"] = "sexual_exploitation"
        return ProtectionDecision(level=level, reasons=reasons, notes=notes)

    # 4) Hate / targeted harm
    if _contains_hate_or_targeting(user_text):
        level = ProtectionLevel.BLOCK
        reasons.append("Detected language suggesting targeted group harm.")
        notes["category"] = "hate_or_targeted_harm"
        return ProtectionDecision(level=level, reasons=reasons, notes=notes)

    # 5) If caller tagged high-risk by context
    if context and context.tags:
        lowered = [t.lower() for t in context.tags]
        if any(t in {"self-harm-risk", "suicide-risk"} for t in lowered):
            level = ProtectionLevel.WARN
            reasons.append("Context tags indicate elevated self-harm risk.")
            notes["category"] = "elevated_risk"

    # If nothing severe triggered, return allow/warn.
    if not reasons:
        reasons.append("No high-risk content detected by simple rules.")
        notes["category"] = "low_risk"

    return ProtectionDecision(level=level, reasons=reasons, notes=notes)


# ---------------------------------------------------------------------------
# Simple helper for other modules
# ---------------------------------------------------------------------------


def apply_protection_to_response(
    user_text: str,
    model_reply: str,
    context: Optional[ProtectionContext] = None,
) -> Dict[str, Any]:
    """
    Wrap a model reply with protection metadata.

    This does not actually change `model_reply`. It just:
    - runs evaluation
    - returns a dict that other layers can use to decide what to show.

    Caller can:
    - show reply if decision.is_allowed()
    - swap in a safer message if decision.level == BLOCK
    - log decision.reasons for audits
    """
    decision = evaluate_protection(user_text=user_text, context=context)

    return {
        "decision": decision,
        "reply": model_reply,
        "allowed": decision.is_allowed(),
    }