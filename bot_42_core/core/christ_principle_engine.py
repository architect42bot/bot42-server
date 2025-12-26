"""
Christ Principle Engine
-----------------------
This module merges:
- PrinciplesEngine (moral foundations)
- ChristFramework (behavioral archetype)
- EpistemicsEngine (truth classification)

It creates a unified evaluation system 42 can use to:
- Judge whether an action/message aligns with Christ-like ethics
- Score responses for compassion, truth, justice, humility, and autonomy
- Provide explanations for *why* a decision is ethical or not
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from bot_42_core.core.principles import PrinciplesEngine, PrincipleDomain
from bot_42_core.core.christ_framework import ChristFramework
from bot_42_core.core.epistemics import EpistemicEngine, EpistemicLevel


@dataclass
class MoralAssessment:
    score: float
    confidence: float
    notes: List[str]
    domains_triggered: List[str]
    christ_traits_applied: List[str]
    epistemic_level: str


class ChristPrincipleEngine:

    def __init__(self):
        self.principles = PrinciplesEngine()
        self.christ = ChristFramework()
        self.epistemics = EpistemicEngine()

    def evaluate(self, text: str) -> MoralAssessment:
        """
        Main evaluation method.
        Returns a holistic Christ-aligned ethical assessment.
        """
        epistemic = self.epistemics.label(text)

        domains = []
        if epistemic["epistemic_level"] == EpistemicLevel.FACT:
            domains.append("truth")
        if epistemic["epistemic_level"] == EpistemicLevel.METAPHYSICAL:
            domains.append("mercy")  # metaphysics handled gently
        if epistemic["epistemic_level"] == EpistemicLevel.SPECULATIVE:
            domains.append("uncertainty")

        matched_principles = self.principles.relevant_to_domains(domains)
        matched_traits = self._match_christ_traits(text)

        total_weight = sum([p.get("weight", 1) for p in matched_principles]) \
                       + sum([t["weight"] for t in matched_traits])

        score = min(1.0, total_weight / 50)  # normalize score
        confidence = epistemic.get("confidence", 0.5)

        notes = [
            f"Epistemic level: {epistemic['epistemic_level']}",
            f"Principles applied: {[p['id'] for p in matched_principles]}",
            f"Christ traits applied: {[t['id'] for t in matched_traits]}"
        ]

        return MoralAssessment(
            score=score,
            confidence=confidence,
            notes=notes,
            domains_triggered=domains,
            christ_traits_applied=[t["id"] for t in matched_traits],
            epistemic_level=epistemic["epistemic_level"])

    def _match_christ_traits(self, text: str) -> List[Dict[str, Any]]:
        """
        Simple keyword-based matcher for determining which Christ traits apply.
        Future versions can use NLP, sentiment, etc.
        """
        lowered = text.lower()
        matches = []

        for trait in self.christ.list_traits():
            if any(kw in lowered for kw in [
                    "help", "save", "hurt", "truth", "care", "compassion",
                    "mercy", "protect", "vulnerable"
            ]):
                matches.append(trait)

        return matches
