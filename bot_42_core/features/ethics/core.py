from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Tuple, Iterable, Optional, Literal, Any
import math

DEFAULT_PILLARS: Tuple[str, ...] = (
    "truthfulness", "compassion", "agency", "justice", "stewardship", "humility", "hope"
)

@dataclass(frozen=True)
class OptionEval:
    """
    label: human-readable option name.
    scores: per-pillar integer scores (0–3 recommended). Missing pillars will be treated as 0.
    notes: short, human-readable rationale for this option.
    """
    label: str
    scores: Dict[str, int]
    notes: str = ""

    def score_for(self, pillar: str) -> int:
        return int(self.scores.get(pillar, 0))

    def min_pillar(self, pillars: Iterable[str]) -> int:
        return min(self.score_for(p) for p in pillars)

    def sum_score(self, pillars: Iterable[str]) -> int:
        return sum(self.score_for(p) for p in pillars)

    def normalized(self, pillars: Iterable[str], lo: int = 0, hi: int = 3) -> "OptionEval":
        """Clamp all provided scores to [lo, hi] and fill missing pillars with 0."""
        clamped = {}
        for p in pillars:
            v = self.scores.get(p, 0)
            try:
                v = int(v)
            except Exception:
                v = 0
            clamped[p] = max(lo, min(hi, v))
        return OptionEval(label=self.label, scores=clamped, notes=self.notes)

def _normalize_pillars(pillars: Optional[Iterable[str]]) -> Tuple[str, ...]:
    if not pillars:
        return DEFAULT_PILLARS
    uniq = []
    seen = set()
    for p in pillars:
        key = str(p).strip().lower()
        if key and key not in seen:
            uniq.append(key)
            seen.add(key)
    return tuple(uniq) if uniq else DEFAULT_PILLARS

def _rank_options(options: List[OptionEval], pillars: Tuple[str, ...]) -> List[OptionEval]:
    """
    Rank by maximin (best worst-pillar score), then by total sum, then by label for determinism.
    """
    # Normalize/clamp scores first
    normed = [o.normalized(pillars) for o in options]
    return sorted(
        normed,
        key=lambda o: (o.min_pillar(pillars), o.sum_score(pillars), o.label.lower()),
        reverse=True,
    )

def high_stakes(domain: str, high_stakes_domains: Iterable[str]) -> bool:
    d = (domain or "").strip().lower()
    return any(d == (x or "").strip().lower() for x in high_stakes_domains)

def ethical_reply(
    domain: str,
    user_text: str,
    options: List[OptionEval],
    cfg: Dict,
    pillars: Optional[Iterable[str]] = None,
) -> Dict:
    """
    Decide among options using a maximin rule across ethical pillars.

    Returns a JSON-serializable dict with:
      - preface: optional warning for high-stakes domains
      - choice: chosen option (dict)
      - explanation: brief transparency note
      - alternatives: remaining options in ranked order (list of dicts)
      - metrics: min/sum scores for traceability
    """
    # Guardrails
    pillars_t = _normalize_pillars(pillars or cfg.get("pillars"))
    if not options:
        return {
            "preface": "",
            "choice": None,
            "explanation": "No options were provided to evaluate.",
            "alternatives": [],
            "metrics": {"pillars": pillars_t, "reason": "empty_options"},
        }

    ranked = _rank_options(options, pillars_t)
    chosen = ranked[0]

    stakes_preface = ""
    if high_stakes(domain, cfg.get("safety", {}).get("high_stakes_domains", [])):
        stakes_preface = "This is high-stakes, so I’ll be careful and transparent."

    explanation = (
        f"I chose **{chosen.label}** because it maximizes the minimum pillar score "
        f"and has a strong overall balance across {', '.join(pillars_t)}. "
        f"Safeguards: privacy-minimal; opt-in for any data save."
    )

    def pack(o: OptionEval) -> Dict:
        return {
            **asdict(o),
            "min_pillar": o.min_pillar(pillars_t),
            "sum_score": o.sum_score(pillars_t),
        }

    return {
        "preface": stakes_preface,
        "choice": pack(chosen),
        "explanation": explanation,
        "alternatives": [pack(o) for o in ranked[1:]],
        "metrics": {
            "pillars": pillars_t,
            "rule": "maximin_then_sum",
            "domain": domain,
        },
    }

# ---------------------------------------------------------------------------
# D-PHASE ETHICS: message-level screening + corrective replies
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


CorrectionMode = Literal["allow", "redirect", "correct", "refuse"]


@dataclass
class EthicsReport:
    risk_level: RiskLevel
    concerns: List[str]
    recommendation: CorrectionMode
    reasoning: str
    christ_alignment_notes: str

    def to_log_dict(self) -> Dict[str, Any]:
        """Small helper so logs can serialize this cleanly."""
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d


# --- simple keyword heuristics ---------------------------------------------

_SELF_HARM = [
    "kill myself",
    "suicide",
    "end it all",
    "hurt myself",
    "cut myself",
    "overdose",
    "i want to die",
]

_VIOLENCE = [
    "kill him",
    "kill her",
    "kill them",
    "murder",
    "hurt them",
    "beat up",
    "how do i make a bomb",
    "assassinate",
]

_ILLEGAL = [
    "how do i hack",
    "credit card dump",
    "steal wifi",
    "fake id",
    "counterfeit",
    "buy drugs online",
]

_HATE = [
    "exterminate",
    "ethnic cleansing",
    "genocide",
]


def _matches_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in phrases)


def score_message(
    user_message: str,
    conversation_context: Optional[Dict[str, Any]] = None,
) -> EthicsReport:
    """
    Lightweight ethical screening on the user message.

    This is intentionally simple for now: keyword heuristics plus
    a Christ-ethics framing. Later you can plug in a more advanced
    classifier here without changing callers.
    """
    concerns: List[str] = []
    lower = user_message.lower()

    if _matches_any(lower, _SELF_HARM):
        concerns.append("self_harm")

    if _matches_any(lower, _VIOLENCE):
        concerns.append("violence")

    if _matches_any(lower, _ILLEGAL):
        concerns.append("illicit_behavior")

    if _matches_any(lower, _HATE):
        concerns.append("hate")

    if not concerns:
        return EthicsReport(
            risk_level=RiskLevel.LOW,
            concerns=[],
            recommendation="allow",
            reasoning="No high-risk patterns detected in this message.",
            christ_alignment_notes=(
                "No direct conflict with compassion, justice, or care for others."
            ),
        )

    # Decide risk & recommendation
    if "self_harm" in concerns or "violence" in concerns or "hate" in concerns:
        risk = RiskLevel.HIGH
        recommendation: CorrectionMode = "correct"
        reasoning = (
            "Detected content about harming self or others. 42 must avoid enabling "
            "harm and instead offer care, redirection, or crisis support."
        )
    else:
        # e.g. purely illicit / lower-grade stuff
        risk = RiskLevel.MEDIUM
        recommendation = "redirect"
        reasoning = (
            "Detected potentially illegal or unethical behavior. 42 should refuse to "
            "help with wrongdoing and redirect toward lawful, constructive options."
        )

    christ_notes = (
        "Act with compassion, protect life, do not enable wrongdoing, and steer the "
        "user toward light, safety, and responsibility."
    )

    return EthicsReport(
        risk_level=risk,
        concerns=concerns,
        recommendation=recommendation,
        reasoning=reasoning,
        christ_alignment_notes=christ_notes,
    )


def build_corrective_reply(
    report: EthicsReport,
    user_message: str,
) -> str:
    """
    Generate a corrective / redirecting reply rooted in Christ-ethics.
    This is used when we *do not* forward the raw query to the LLM.
    """

    if "self_harm" in report.concerns:
        return (
            "I’m really glad you said something. I can’t help you harm yourself, "
            "but I care about your safety and well-being.\n\n"
            "You deserve support, not judgment. If you’re in immediate danger, "
            "please contact local emergency services or a crisis line right away. "
            "If you’d like, I can help you think through what you’re feeling, or "
            "help you plan a few small, safe next steps.\n\n"
            "You are not alone, and your life has real value."
        )

    if "violence" in report.concerns or "hate" in report.concerns:
        return (
            "I can’t help with harming or targeting anyone. That would go against "
            "everything 42 stands for: justice, compassion, and protecting people.\n\n"
            "If you’re angry or hurt by something that happened, we *can* talk about "
            "that. I can help you unpack what you’re feeling, look at safer ways to "
            "respond, or think through how to seek real accountability without "
            "crossing ethical lines."
        )

    if "illicit_behavior" in report.concerns:
        return (
            "I’m not able to help with anything illegal or deceptive. 42 is built to "
            "work within honesty, responsibility, and respect for others.\n\n"
            "If there’s a problem you’re trying to solve—like money stress, access "
            "issues, or conflict—we can look for ethical, legal strategies together."
        )

    # Fallback for unknown concerns
    return (
        "Something in that request conflicts with 42’s ethical core, so I can’t do "
        "what you’re asking.\n\n"
        "I *can* help you explore what’s driving the situation and look for paths "
        "that are honest, safe, and aligned with compassion and justice."
    )

def attach_ethics_to_log(
    base_log: Dict[str, Any],
    report: EthicsReport,
) -> Dict[str, Any]:
    """
    Convenience helper: merge ethics metadata into a log entry.
    """
    base_log = dict(base_log)  # shallow copy
    base_log["ethics"] = report.to_log_dict()
    return base_log