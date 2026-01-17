# core/response_formatter.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ResponseParts:
    mirror_intent: str = ""
    main: str = ""
    uncertainty: str = ""
    next_step: str = ""
    question: str = ""


def infer_mirror_intent(user_text: str) -> str:
    t = (user_text or "").strip()
    if not t:
        return ""
    if t.endswith("?"):
        return "Sounds like you’re asking for a clear, grounded answer."
    return "Sounds like you’re thinking through this carefully."


def format_structured_response(
    user_text: str,
    analysis: Optional[str] = None,
    ask_question_if_needed: bool = True,
) -> str:
    """
    Minimal post-processing formatter.
    - Keeps output structured
    - Light epistemic labeling
    - No dependencies on RoutedTurn/ConversationState
    """
    parts = ResponseParts()
    parts.mirror_intent = infer_mirror_intent(user_text)

    parts.main = analysis or "Here’s what I can say from the information given."
    # Keep uncertainty gentle; you can wire your real epistemics state later
    # parts.uncertainty = ""

    parts.next_step = "If you want, share one constraint or example and I’ll tighten the answer."

    if ask_question_if_needed:
        # You turned this off in chat_pipeline anyway, but leaving it here is fine.
        parts.question = ""

    out_lines: List[str] = []
    if parts.mirror_intent:
        out_lines.append(parts.mirror_intent)
    if parts.main:
        out_lines.append(parts.main)
    if parts.uncertainty:
        out_lines.append(parts.uncertainty)
    if parts.next_step:
        out_lines.append(parts.next_step)
    if parts.question:
        out_lines.append(parts.question)

    return "\n\n".join([ln.strip() for ln in out_lines if ln and ln.strip()])
