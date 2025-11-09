from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import re
import textwrap
import logging

log = logging.getLogger("bot42.personality")


# ---------- Models ----------
@dataclass
class Persona:
    key: str
    name: str
    description: str
    style: Dict[str, Any] = field(default_factory=dict)
    tics: List[str] = field(default_factory=list)
    disclaimers: List[str] = field(default_factory=list)
    banned_topics: List[str] = field(default_factory=list)
    max_len: int = 800  # soft cap; we'll trim politely


# ---------- Presets ----------
def preset_persona(key: str) -> Persona:
    k = key.lower().strip()

    if k in ("sage", "mentor", "guide"):
        return Persona(
            key="sage",
            name="The Sage",
            description="Calm, precise mentor. Prioritizes clarity and structure.",
            style={"tone": "calm", "tempo": "steady", "emojis": False, "caps": False, "bullets": True, "compact": True},
            tics=[],
            disclaimers=[
                "I won’t fabricate details; if I’m unsure, I’ll say so.",
            ],
            banned_topics=[],
            max_len=900,
        )

    if k in ("hype", "coach", "energize"):
        return Persona(
            key="hype",
            name="The Hype Coach",
            description="High-energy encourager. Short punchy sentences. Momentum > ornament.",
            style={"tone": "upbeat", "tempo": "fast", "emojis": True, "caps": False, "bullets": False, "compact": True},
            tics=["Let’s go.", "You’ve got this."],
            disclaimers=[],
            banned_topics=[],
            max_len=600,
        )

    if k in ("deadpan", "dry", "minimal"):
        return Persona(
            key="deadpan",
            name="Deadpan Pro",
            description="Dry, minimal, unflappable. Says the most with the least.",
            style={"tone": "neutral", "tempo": "slow", "emojis": False, "caps": False, "bullets": False, "compact": True},
            tics=[],
            disclaimers=[],
            banned_topics=[],
            max_len=400,
        )

    if k in ("scout", "ops", "tactical"):
        return Persona(
            key="scout",
            name="Ops Scout",
            description="Tactical and practical. Always gives next steps and risks.",
            style={"tone": "practical", "tempo": "steady", "emojis": False, "caps": False, "bullets": True, "compact": True},
            tics=["Bottom line:", "Heads-up:"],
            disclaimers=["No guarantees; we’ll adapt as new info lands."],
            banned_topics=[],
            max_len=800,
        )

    if k in ("poet", "muse"):
        return Persona(
            key="poet",
            name="Urban Muse",
            description="Brief, vivid imagery. A single good line beats a paragraph.",
            style={"tone": "lyrical", "tempo": "slow", "emojis": False, "caps": False, "bullets": False, "compact": True},
            tics=[],
            disclaimers=[],
            banned_topics=[],
            max_len=300,
        )

    # default
    return Persona(
        key="neutral",
        name="Neutral",
        description="Straightforward helper with balanced tone.",
        style={"tone": "neutral", "tempo": "steady", "emojis": False, "caps": False, "bullets": False, "compact": True},
        tics=[],
        disclaimers=[],
        banned_topics=[],
        max_len=700,
    )


# ---------- Guardrails (lightweight) ----------
_SENSITIVE_PATTERNS = [
    r"\b(ssn|social\s*security\s*number)\b",
    r"\bcredit\s*card\b",
    r"\bbank\s*account\b",
]

def _sanitize(text: str) -> str:
    redacted = text
    for pat in _SENSITIVE_PATTERNS:
        redacted = re.sub(pat, "[redacted]", redacted, flags=re.I)
    return redacted


def _blocked(text: str, persona: Persona) -> Optional[str]:
    if not persona.banned_topics:
        return None
    for topic in persona.banned_topics:
        if topic and topic.lower() in text.lower():
            return f"I can’t discuss **{topic}**. Pick a different angle and I’ll help."
    return None


# ---------- Styling helpers ----------
def _apply_style(body: str, persona: Persona) -> str:
    s = persona.style or {}
    compact = bool(s.get("compact", True))
    bullets = bool(s.get("bullets", False))
    emojis = bool(s.get("emojis", False))

    # Normalize whitespace
    body = re.sub(r"[ \t]+", " ", body).strip()
    if compact:
        body = re.sub(r"\n{3,}", "\n\n", body)

    # Optional bullets: convert simple steps into bullets if requested
    if bullets:
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        if len(lines) > 1 and not any(ln.startswith(("-", "•")) for ln in lines):
            lines = [f"- {ln}" for ln in lines]
        body = "\n".join(lines)

    # Emojis: sprinkle carefully (front-load only)
    if emojis:
        if not body.startswith(("✅", "🔥", "💡", "⚙️", "🧭")):
            body = f"💡 {body}"

    # Enforce soft max length
    if len(body) > persona.max_len:
        body = body[: persona.max_len - 20].rstrip() + " …"

    # Wrap long lines (console-friendly)
    body = "\n".join(textwrap.fill(ln, width=100) for ln in body.splitlines())

    return body


# ---------- Public API ----------
class Personality:
    def __init__(self, key: str = "neutral") -> None:
        self.persona = preset_persona(key)
        log.info("Personality loaded: %s (%s)", self.persona.name, self.persona.key)

    def set(self, key: str) -> "Personality":
        self.persona = preset_persona(key)
        log.info("Personality switched: %s (%s)", self.persona.name, self.persona.key)
        return self

    def reply(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Produce a styled reply with light guardrails. Returns structured output."""
        context = context or {}

        # guardrails
        reason = _blocked(message, self.persona)
        if reason:
            body = reason
        else:
            clean = _sanitize(message)
            body = self._draft(clean, context)

        body = _apply_style(body, self.persona)

        return {
            "ok": True,
            "persona": self.persona.key,
            "name": self.persona.name,
            "text": body,
            "disclaimers": list(self.persona.disclaimers),
        }

    # ----- internal drafting -----
    def _draft(self, msg: str, ctx: Dict[str, Any]) -> str:
        style = self.persona.style or {}
        tone = style.get("tone", "neutral")

        # Tiny heuristics to produce a response skeleton
        if self.persona.key == "sage":
            parts = []
            parts.append("Here’s the move:")
            if "ask" in ctx:
                parts.append(ctx["ask"])
            parts.append("1) Clarify the objective.")
            parts.append("2) Choose the smallest next action that proves progress.")
            parts.append("3) Close the loop and log the result.")
            return "\n".join(parts)

        if self.persona.key == "hype":
            base = f"{msg.strip().capitalize()}"
            suffix = " Let’s get it."
            return f"{base}. {suffix}"

        if self.persona.key == "deadpan":
            return "Noted. " + (msg.strip().capitalize() or "Proceed.")

        if self.persona.key == "scout":
            return "\n".join([
                "Bottom line:",
                "• Identify constraints.",
                "• Pick a 10-minute action.",
                "• Execute. Log. Adjust.",
            ])

        if self.persona.key == "poet":
            return f"{msg.strip().capitalize()} — like flint on steel, make a spark."

        # default neutral
        return f"{msg.strip().capitalize()}."

# Convenience factory
def load_personality(key: str = "neutral") -> Personality:
    return Personality(key)
