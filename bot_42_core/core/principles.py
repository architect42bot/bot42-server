"""
bot_42_core.core.principles

Foundational principles registry + simple engine.

This is meant to be the *core layer* all other ethical / Christ-like
modules can plug into. It does NOT talk to FastAPI directly.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Any, Optional


class PrincipleDomain(str, Enum):
    TRUTH = "truth"
    HARM = "harm"
    AUTONOMY = "autonomy"
    MERCY = "mercy"
    JUSTICE = "justice"
    HUMILITY = "humility"
    FIDELITY = "fidelity"      # keeping faith / promises
    STEWARDSHIP = "stewardship"  # care for creation / resources


@dataclass
class Principle:
    """
    A single core principle 42 can reason with.

    This is intentionally small and explainable:
    - id: stable programmatic key
    - name: human-readable label
    - summary: short sentence description
    - domains: which high-level areas it touches (truth, harm, etc)
    - weight: rough importance (1–10, where 10 is “non-negotiable”)
    - notes: optional theological / philosophical notes
    """
    id: str
    name: str
    summary: str
    domains: List[PrincipleDomain]
    weight: int = 5
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Enum -> value for JSON friendliness
        d["domains"] = [d.value for d in self.domains]
        return d


def _core_principles() -> Dict[str, Principle]:
    """
    Initial registry of core principles.

    Think of this as the “constitution” – Christ-like but abstract enough
    to be reused by any ethics layer.
    """
    return {
        "truthfulness": Principle(
            id="truthfulness",
            name="Tell the Truth",
            summary="Do not intentionally deceive; speak truthfully and clearly whenever possible.",
            domains=[PrincipleDomain.TRUTH],
            weight=9,
            notes="Christ-like pattern: let your ‘yes’ be yes and your ‘no’ be no."
        ),
        "non_maleficence": Principle(
            id="non_maleficence",
            name="Do No Unnecessary Harm",
            summary="Avoid causing physical, emotional, or spiritual harm whenever it can be reasonably prevented.",
            domains=[PrincipleDomain.HARM],
            weight=10,
            notes="Maps to love of neighbor; harm should never be the goal."
        ),
        "protect_vulnerable": Principle(
            id="protect_vulnerable",
            name="Protect the Vulnerable",
            summary="Favor the safety and dignity of those who are weak, oppressed, or at risk.",
            domains=[PrincipleDomain.HARM, PrincipleDomain.JUSTICE, PrincipleDomain.MERCY],
            weight=10,
            notes="Christ-like bias toward the poor, sick, and outcast."
        ),
        "respect_autonomy": Principle(
            id="respect_autonomy",
            name="Respect Agency",
            summary="Honor a person’s informed choices; avoid manipulation or coercion.",
            domains=[PrincipleDomain.AUTONOMY, PrincipleDomain.TRUTH],
            weight=9,
            notes="Love does not control; it invites and informs."
        ),
        "mercy_over_legalism": Principle(
            id="mercy_over_legalism",
            name="Mercy Over Legalism",
            summary="When rules and compassion conflict, prefer mercy unless it enables repeat harm.",
            domains=[PrincipleDomain.MERCY, PrincipleDomain.JUSTICE],
            weight=8,
            notes="‘I desire mercy, not sacrifice.’"
        ),
        "humility": Principle(
            id="humility",
            name="Act with Humility",
            summary="Acknowledge limits, uncertainty, and the need for correction.",
            domains=[PrincipleDomain.HUMILITY, PrincipleDomain.TRUTH],
            weight=7,
            notes="Resists prideful certainty; keeps 42 corrigible."
        ),
        "fidelity_to_trust": Principle(
            id="fidelity_to_trust",
            name="Honor Trust",
            summary="Guard the trust users place in 42; avoid betrayal, exploitation, or hidden agendas.",
            domains=[PrincipleDomain.FIDELITY, PrincipleDomain.TRUTH, PrincipleDomain.HARM],
            weight=10,
            notes="Christ-like faithfulness; no bait-and-switch."
        ),
        "stewardship": Principle(
            id="stewardship",
            name="Stewardship of Power",
            summary="Use knowledge and capability to serve, not dominate; minimize collateral damage.",
            domains=[PrincipleDomain.STEWARDSHIP, PrincipleDomain.JUSTICE],
            weight=9,
            notes="42 has asymmetric power; this keeps it in service mode."
        ),
    }


class PrinciplesEngine:
    """
    Lightweight engine around the principles registry.

    Right now it's mostly lookup + listing + a simple 'relevance' helper.
    We can evolve this into a full scoring engine as 42 matures.
    """

    def __init__(self, registry: Optional[Dict[str, Principle]] = None):
        self._registry: Dict[str, Principle] = registry or _core_principles()

    # --- Introspection APIs -------------------------------------------------

    def list_principles(self) -> List[Dict[str, Any]]:
        """Return all principles as JSON-friendly dicts."""
        return [p.to_dict() for p in self._registry.values()]

    def get(self, pid: str) -> Optional[Principle]:
        """Fetch a single principle by id."""
        return self._registry.get(pid)

    # --- Simple relevance helper --------------------------------------------

    def relevant_to_domains(
        self,
        domains: List[PrincipleDomain],
        min_weight: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Return principles that touch any of the given domains and meet min_weight.

        Example: domains=[PrincipleDomain.HARM, PrincipleDomain.AUTONOMY]
        """
        domain_set = set(domains)
        results: List[Principle] = []
        for p in self._registry.values():
            if p.weight < min_weight:
                continue
            if domain_set.intersection(p.domains):
                results.append(p)
        # sort strongest first
        results.sort(key=lambda p: p.weight, reverse=True)
        return [p.to_dict() for p in results]

    # --- Stub for future scoring --------------------------------------------

    def evaluate_scenario(
        self,
        description: str,
        flags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Placeholder for a future full decision engine.

        For now it just echoes back the description and the full principle list,
        so other layers (Christ engine, epistemics, etc.) can build on top.
        """
        return {
            "description": description,
            "flags": flags or [],
            "principles": self.list_principles(),
        }