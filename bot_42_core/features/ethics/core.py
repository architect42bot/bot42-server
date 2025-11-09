from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Iterable, Optional
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