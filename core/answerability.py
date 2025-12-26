# core/answerability.py
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Answerability(str, Enum):
    ANSWERABLE = "answerable"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_ENOUGH_INFO = "not_enough_info"
    REQUIRES_EXTERNAL_DATA = "requires_external_data"
    HIGH_STAKES = "high_stakes"


@dataclass
class GateResult:
    verdict: Answerability
    questions: List[str]
    notes: str = ""
    confidence: float = 0.5 # internal use; keep rough


HIGH_STAKES_KEYWORDS = {
    "chest pain", "suicidal", "overdose", "stroke", "lawsuit", "tax", "invest",
    "bankruptcy", "dosage", "prescription", "legal advice"
}

EXTERNAL_DATA_TRIGGERS = {
    "today", "latest", "current", "right now", "price", "stock", "weather",
    "score", "schedule", "breaking news"
}


def _contains_any(text: str, phrases: set[str]) -> bool:
    t = text.lower()
    return any(p in t for p in phrases)


def answerability_gate(user_text: str) -> GateResult:
    t = user_text.strip()
    tl = t.lower()

    if not t:
        return GateResult(
            verdict=Answerability.NEEDS_CLARIFICATION,
            questions=["What would you like help with?"],
            notes="Empty input."
        )

    # High-stakes fast-path
    if _contains_any(tl, HIGH_STAKES_KEYWORDS):
        return GateResult(
            verdict=Answerability.HIGH_STAKES,
            questions=[
                "Can you share a bit more detail (symptoms/situation, timing, and what you’ve tried so far)?",
                "What outcome are you trying to achieve (information, next steps, or a decision)?"
            ],
            notes="High-stakes keywords detected.",
            confidence=0.8
        )

    # External-data fast-path (if 42 cannot browse)
    if _contains_any(tl, EXTERNAL_DATA_TRIGGERS):
        return GateResult(
            verdict=Answerability.REQUIRES_EXTERNAL_DATA,
            questions=[
                "I can help, but I’ll need the specific details or a source (e.g., location/date/link/screenshot). What do you have?"
            ],
            notes="Likely requires up-to-date or external data.",
            confidence=0.7
        )

    # Underspecified heuristics: very short + vague
    if len(t.split()) < 4 and not any(ch.isdigit() for ch in t):
        return GateResult(
            verdict=Answerability.NEEDS_CLARIFICATION,
            questions=[
                "Can you tell me what you’re trying to do and what context I should assume?"
            ],
            notes="Too short/vague to answer well.",
            confidence=0.6
        )

    # Default: answerable
    return GateResult(
        verdict=Answerability.ANSWERABLE,
        questions=[],
        notes="Appears answerable with given info.",
        confidence=0.6
    )