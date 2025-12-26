# anti_hallucination.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class AHConfig:
    # If the assistant says it used tools/web/files/etc but you didn’t actually run them, flag it.
    forbid_fake_tool_claims: bool = True

    # If user asks for “exact/quote/source/link/current/latest”, require citations or explicit uncertainty.
    require_evidence_on_high_precision: bool = True

    # If answer contains lots of strong certainty words without evidence, soften it.
    soften_overconfidence: bool = True

    # Max number of "hard claims" before we ask clarifying / mark uncertainty
    hard_claim_threshold: int = 8


TOOL_CLAIM_PATTERNS = [
    r"\bI (searched|looked up|browsed|checked) (the )?(web|internet)\b",
    r"\bI (ran|executed) (the )?(code|script)\b",
    r"\bI (opened|read) (your )?(file|pdf|doc|document)\b",
    r"\bI (checked|looked at) (your )?(calendar|gmail|email)\b",
    r"\bI used (tool|tools)\b",
]

HIGH_PRECISION_TRIGGERS = [
    "exact", "exactly", "verbatim", "quote", "citation", "source", "link",
    "latest", "current", "today", "now", "up-to-date", "verify", "prove"
]

OVERCONFIDENT_WORDS = [
    "definitely", "guaranteed", "certainly", "always", "never", "100%", "undeniably"
]

HARD_CLAIM_HEURISTIC = re.compile(
    r"\b(is|are|was|were|will be|causes|means|proves)\b", re.IGNORECASE
)


def _contains_any(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return any(n in t for n in needles)


def _matches_any_regex(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _count_hard_claims(text: str) -> int:
    return len(HARD_CLAIM_HEURISTIC.findall(text))


def _soften_confidence(text: str) -> str:
    # Replace some absolute language with calibrated language.
    replacements = {
        "definitely": "very likely",
        "certainly": "likely",
        "guaranteed": "expected",
        "always": "typically",
        "never": "rarely",
        "100%": "with high confidence",
        "undeniably": "strongly",
    }
    out = text
    for k, v in replacements.items():
        out = re.sub(rf"\b{k}\b", v, out, flags=re.IGNORECASE)
    return out


def anti_hallucination_guard(
    user_text: str,
    assistant_text: str,
    *,
    tool_context: Optional[Dict] = None,
    config: Optional[AHConfig] = None
) -> Tuple[str, List[str]]:
    """
    Returns (possibly_modified_text, flags)

    tool_context can be something like:
      {"web_used": False, "files_used": False, "code_executed": False}
    """
    cfg = config or AHConfig()
    flags: List[str] = []
    tool_context = tool_context or {}

    out = assistant_text

    # 1) Block fake tool claims if you didn't do them
    if cfg.forbid_fake_tool_claims:
        claimed_tools = _matches_any_regex(out, TOOL_CLAIM_PATTERNS)
        web_used = bool(tool_context.get("web_used"))
        files_used = bool(tool_context.get("files_used"))
        code_executed = bool(tool_context.get("code_executed"))
        any_used = web_used or files_used or code_executed

        if claimed_tools and not any_used:
            flags.append("fake_tool_claim")
            # Replace with honest phrasing
            out = re.sub(r"\bI (searched|looked up|browsed|checked)\b.*?\b(web|internet)\b",
                         "I didn’t look anything up live here, but based on what you shared",
                         out, flags=re.IGNORECASE)

    # 2) If user is asking for high-precision, require evidence or add a disclaimer
    if cfg.require_evidence_on_high_precision and _contains_any(user_text, HIGH_PRECISION_TRIGGERS):
        # If no obvious citations/links and response is assertive, add calibration footer
        has_citation_like = bool(re.search(r"\[.*?\]\(.*?\)", out)) or "cite" in out.lower()
        if not has_citation_like:
            flags.append("precision_without_evidence")
            out += "\n\nNote: If you need this verified or sourced, I can help you structure what to check and how—" \
                   "but I’m relying only on the info in this chat."

    # 3) Soften overconfidence when it smells like a hallucination risk
    if cfg.soften_overconfidence:
        hard_claims = _count_hard_claims(out)
        if _contains_any(out, OVERCONFIDENT_WORDS) and hard_claims >= 3:
            flags.append("overconfident_tone_softened")
            out = _soften_confidence(out)

    # 4) If it's making tons of claims, encourage narrowing
    if _count_hard_claims(out) >= (cfg.hard_claim_threshold):
        flags.append("many_hard_claims")
        out += "\n\nIf you want, tell me which part you need to be most exact about, and I’ll narrow it down."

    return out, flags