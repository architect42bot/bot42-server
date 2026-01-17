# core/epistemic_pipeline.py
"""
Epistemic Pipeline (Project 42)

Purpose
-------
This module does NOT "answer" questions.

It produces an EpistemicFrame: a structured view of what has been presented,
how credible it seems (given limited information), what assumptions are being
made, what is missing, and what can be deduced (boundedly) from the accepted
claims.

Design posture
--------------
- Treat user-provided "facts" as *claims* until assessed.
- Prefer *classification + next-step guidance* over bluffing certainty.
- Support "I don't know, but hold on" behavior by routing ambiguity to:
  (a) clarifying questions
  (b) scoped deductions
  (c) verification suggestions

No side effects. No network. No model calls.
Pure input -> output.

Integration idea
----------------
Call `run_epistemic_pipeline(user_text, context=...)` early in your chat pipeline.
Log the returned frame. Initially, you can ignore its suggestions; later you can
use it to gate research, ask clarifiers, or adjust response confidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
# ----------------------------
# Labels & data structures
# ----------------------------

class EvidenceType(str, Enum):
    NONE = "none"
    ASSERTION = "assertion"
    ANECDOTE = "anecdote"
    OBSERVATION = "observation"
    DOCUMENT = "document"
    MEASUREMENT = "measurement"
    EXPERT = "expert"
    CONSENSUS = "consensus"
    LINK = "link"


class EpistemicLabel(str, Enum):
    SUPPORTED = "supported"
    PLAUSIBLE = "plausible"
    UNVERIFIED = "unverified"
    SPECULATIVE = "speculative"
    CONTRADICTORY = "contradictory"
    LOW_CREDIBILITY = "low_credibility"


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Claim:
    """A single extracted claim from user content (or upstream context)."""
    text: str
    speaker: str = "user"  # user/system/tool/other
    evidence_type: EvidenceType = EvidenceType.ASSERTION
    source_hint: Optional[str] = None  # e.g., 'news', 'personal', 'friend', 'link'
    polarity: str = "affirm"  # affirm/deny/unknown
    entities: List[str] = field(default_factory=list)


@dataclass
class ClaimAssessment:
    """Assessment for a single claim."""
    claim: Claim
    label: EpistemicLabel
    confidence: ConfidenceBand
    reasons: List[str] = field(default_factory=list)
    needed_to_verify: List[str] = field(default_factory=list)


@dataclass
class Deduction:
    """A bounded inference derived from accepted claims (and explicit assumptions)."""
    statement: str
    from_claims: List[int] = field(default_factory=list)  # indices into accepted_claims
    assumptions: List[str] = field(default_factory=list)
    confidence: ConfidenceBand = ConfidenceBand.LOW


@dataclass
class EpistemicFrame:
    """Full output of the epistemic pipeline."""
    accepted: List[ClaimAssessment] = field(default_factory=list)
    rejected: List[ClaimAssessment] = field(default_factory=list)
    uncertain: List[ClaimAssessment] = field(default_factory=list)

    assumptions: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)

    deductions: List[Deduction] = field(default_factory=list)

    missing_context: List[str] = field(default_factory=list)
    clarifying_questions: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)

    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict for logging/JSON."""
        return asdict(self)

@property
def needs_clarification(self) -> bool:
    missing = getattr(self, "missing_context", []) or []
    qs = getattr(self, "clarifying_questions", []) or []
    return bool(missing or qs)


@property
def clarifying_question(self) -> str:
    qs = getattr(self, "clarifying_questions", None) or []
    if qs:
        return qs[0]
    missing = getattr(self, "missing_context", None) or []
    if missing:
        return f"One quick question to avoid guessing: {missing[0]}"
    return "One quick question to avoid guessing: what’s the main constraint you care about most here?"
# ----------------------------
# Extraction helpers
# ----------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Simple patterns that hint evidence types
_LINK_RE = re.compile(r"https?://\S+")
_QUOTE_RE = re.compile(r'“[^”]{5,}”|"[^"]{5,}"')
_REPORTING_VERBS_RE = re.compile(
    r"\b(saw|heard|read|watched|noticed|measured|tested|found|proved|confirmed|reported|said|claims?)\b",
    re.IGNORECASE,
)

# Heuristics that often indicate speculation
_SPECULATION_RE = re.compile(r"\b(might|maybe|could|possibly|hypothetically|seems|I think|I feel)\b", re.IGNORECASE)

# Heuristics that often indicate stronger certainty language
_CERTAINTY_RE = re.compile(r"\b(definitely|certainly|proven|undeniable|always|never)\b", re.IGNORECASE)

# Contradiction cue words
_CONTRAST_RE = re.compile(r"\b(but|however|yet|although|though)\b", re.IGNORECASE)


def _guess_evidence_type(sentence: str) -> EvidenceType:
    s = sentence.strip()
    if _LINK_RE.search(s):
        return EvidenceType.LINK
    if _QUOTE_RE.search(s):
        return EvidenceType.DOCUMENT
    # "I saw / I heard / I measured" etc.
    if _REPORTING_VERBS_RE.search(s):
        # crude refinement: if user says "heard" -> anecdote/observation
        if re.search(r"\bheard\b", s, re.IGNORECASE):
            return EvidenceType.ANECDOTE
        if re.search(r"\bsaw|noticed|watched\b", s, re.IGNORECASE):
            return EvidenceType.OBSERVATION
        if re.search(r"\bmeasured|tested\b", s, re.IGNORECASE):
            return EvidenceType.MEASUREMENT
        if re.search(r"\bread\b", s, re.IGNORECASE):
            return EvidenceType.DOCUMENT
        if re.search(r"\breported\b", s, re.IGNORECASE):
            return EvidenceType.EXPERT
        return EvidenceType.ASSERTION
    return EvidenceType.ASSERTION


def _extract_entities(sentence: str) -> List[str]:
    """
    Very lightweight entity hinting:
    - Proper-ish words (Capitalized) not at start of sentence
    - Simple acronyms / ALLCAPS tokens
    You can replace this with spaCy or your own NER later.
    """
    tokens = re.findall(r"[A-Za-z0-9_-]+", sentence)
    ents: List[str] = []
    for i, t in enumerate(tokens):
        if len(t) >= 2 and t.isupper():
            ents.append(t)
        elif i > 0 and len(t) >= 3 and t[0].isupper() and t[1:].islower():
            ents.append(t)
    # de-dupe while preserving order
    seen = set()
    out: List[str] = []
    for e in ents:
        if e not in seen:
            out.append(e)
            seen.add(e)
    return out


def extract_claims(text: str, speaker: str = "user") -> List[Claim]:
    """
    Extract claims from free text using conservative heuristics.
    - Splits into sentences.
    - Filters out very short fragments.
    """
    raw_parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
    claims: List[Claim] = []

    for part in raw_parts:
        # Ignore very short fragments (noise), but keep short decisive sentences.
        if len(part) < 6:
            continue

        ev = _guess_evidence_type(part)

        polarity = "affirm"
        if re.search(r"\bnot\b|\bnever\b|\bno\b", part, re.IGNORECASE):
            # This is simplistic; it's okay for v1.
            polarity = "deny"

        claims.append(
            Claim(
                text=part,
                speaker=speaker,
                evidence_type=ev,
                source_hint="link" if ev == EvidenceType.LINK else None,
                polarity=polarity,
                entities=_extract_entities(part),
            )
        )

    return claims


# ----------------------------
# Assessment logic
# ----------------------------

def _assess_claim(claim: Claim, all_claims: List[Claim]) -> ClaimAssessment:
    """
    Assign an epistemic label + confidence band.

    IMPORTANT: This is heuristic. The goal is to be conservative and helpful.
    The system should not "declare truth" without evidence. It should classify.
    """
    text = claim.text
    reasons: List[str] = []
    needed: List[str] = []

    # Baseline: unverified assertion
    label = EpistemicLabel.UNVERIFIED
    confidence = ConfidenceBand.LOW

    # Evidence-type adjustment
    if claim.evidence_type == EvidenceType.LINK:
        label = EpistemicLabel.PLAUSIBLE
        confidence = ConfidenceBand.MEDIUM
        reasons.append("Includes a link; credibility depends on the linked source.")
        needed.append("Open the link and verify author/date/claims.")
    elif claim.evidence_type == EvidenceType.MEASUREMENT:
        label = EpistemicLabel.PLAUSIBLE
        confidence = ConfidenceBand.MEDIUM
        reasons.append("Framed as a measurement/test.")
        needed.append("Details: method, instrument, conditions, reproducibility.")
    elif claim.evidence_type in (EvidenceType.DOCUMENT, EvidenceType.EXPERT, EvidenceType.CONSENSUS):
        label = EpistemicLabel.PLAUSIBLE
        confidence = ConfidenceBand.MEDIUM
        reasons.append("Presented as document/expert/consensus.")
        needed.append("Confirm the document/source quality and whether it supports the claim.")
    elif claim.evidence_type in (EvidenceType.OBSERVATION, EvidenceType.ANECDOTE):
        label = EpistemicLabel.UNVERIFIED
        confidence = ConfidenceBand.LOW
        reasons.append("Anecdote/observation; may be accurate but not independently verified.")
        needed.append("Corroboration from additional sources or repeat observation.")

    # Speculation vs certainty cues
    if _SPECULATION_RE.search(text):
        reasons.append("Contains speculation cues (might/maybe/could/etc.).")
        # speculation nudges label downward unless evidence is strong
        if label in (EpistemicLabel.SUPPORTED, EpistemicLabel.PLAUSIBLE):
            label = EpistemicLabel.UNVERIFIED
            confidence = ConfidenceBand.LOW
        else:
            label = EpistemicLabel.SPECULATIVE
            confidence = ConfidenceBand.LOW

    if _CERTAINTY_RE.search(text) and claim.evidence_type == EvidenceType.ASSERTION:
        reasons.append("Strong certainty language without supporting evidence.")
        label = EpistemicLabel.LOW_CREDIBILITY
        confidence = ConfidenceBand.LOW
        needed.append("Provide evidence or reliable source for high-certainty wording.")

    # Detect internal contradictions (simple heuristic)
    # If another claim mentions same entities with opposite polarity, flag contradictory.
    ent_set = set(claim.entities)
    if ent_set:
        for other in all_claims:
            if other is claim:
                continue
            overlap = ent_set.intersection(other.entities)
            if overlap and other.polarity != claim.polarity:
                # if they talk about same entities and one denies, consider contradiction candidate
                label = EpistemicLabel.CONTRADICTORY
                confidence = ConfidenceBand.LOW
                reasons.append(f"Potential contradiction involving entities: {', '.join(sorted(overlap))}.")
                needed.append("Resolve by clarifying scope/time or providing evidence.")
                break

    # If claim is short and purely assertive, keep unverified.
    if claim.evidence_type == EvidenceType.ASSERTION and len(text) < 35 and label != EpistemicLabel.CONTRADICTORY:
        reasons.append("Short assertion; insufficient context to support.")
        needed.append("Add context: who/what/when/where/how known.")

    return ClaimAssessment(
        claim=claim,
        label=label,
        confidence=confidence,
        reasons=reasons,
        needed_to_verify=needed,
    )


def assess_claims(claims: List[Claim]) -> List[ClaimAssessment]:
    return [_assess_claim(c, claims) for c in claims]


# ----------------------------
# Frame building (accepted/rejected/uncertain)
# ----------------------------

def _bucket(assessments: List[ClaimAssessment]) -> Tuple[List[ClaimAssessment], List[ClaimAssessment], List[ClaimAssessment]]:
    accepted: List[ClaimAssessment] = []
    rejected: List[ClaimAssessment] = []
    uncertain: List[ClaimAssessment] = []

    for a in assessments:
        if a.label == EpistemicLabel.SUPPORTED:
            accepted.append(a)
        elif a.label in (EpistemicLabel.LOW_CREDIBILITY,):
            rejected.append(a)
        elif a.label == EpistemicLabel.CONTRADICTORY:
            uncertain.append(a)
        elif a.label in (EpistemicLabel.PLAUSIBLE, EpistemicLabel.UNVERIFIED, EpistemicLabel.SPECULATIVE):
            # conservative: plausible/unverified/speculative all stay uncertain in v1
            uncertain.append(a)
        else:
            uncertain.append(a)

    return accepted, rejected, uncertain


def _derive_missing_context(claims: List[ClaimAssessment]) -> List[str]:
    missing: List[str] = []
    # Heuristic: if many claims have low confidence or needed_to_verify, add general missing items.
    low_count = sum(1 for c in claims if c.confidence == ConfidenceBand.LOW)
    if claims and low_count / max(1, len(claims)) >= 0.6:
        missing.append("More specific context (who/what/when/where) for key claims.")
        missing.append("Sources or evidence for high-impact assertions.")
    return missing


def _build_clarifying_questions(assessments: List[ClaimAssessment], max_q: int = 5) -> List[str]:
    """
    Generate targeted clarifiers from 'needed_to_verify'.
    Keep them short and actionable.
    """
    questions: List[str] = []
    for a in assessments:
        if a.needed_to_verify:
            # Turn the first needed item into a question
            need = a.needed_to_verify[0]
            if "Open the link" in need:
                q = "What is the source behind the link (publisher/author/date), and what exactly does it claim?"
            elif "Details" in need:
                q = "What were the measurement/test details (method, conditions, how repeated)?"
            elif "Confirm" in need:
                q = "Which specific document/source is this based on, and what part supports the claim?"
            elif "Corroboration" in need:
                q = "Is there any second source or repeat observation that supports this?"
            else:
                q = "Can you add the missing context (who/what/when/where/how you know)?"
            if q not in questions:
                questions.append(q)
        if len(questions) >= max_q:
            break
    return questions


def _collect_contradictions(assessments: List[ClaimAssessment]) -> List[str]:
    contradictions: List[str] = []
    for a in assessments:
        if a.label == EpistemicLabel.CONTRADICTORY:
            contradictions.append(a.claim.text)
    return contradictions


def _basic_deductions(accepted: List[ClaimAssessment], assumptions: List[str]) -> List[Deduction]:
    """
    Conservative deductions:
    - Only deduce simple consequences such as "If X is true, then Y is possible/likely"
    - Avoid chain-of-thought; keep deductions short and explicit.

    In v1, we only do minimal, safe deductions:
    - If any accepted claim contains "is/are" + attribute, we can restate it.
    """
    deds: List[Deduction] = []
    for idx, a in enumerate(accepted):
        # naive extraction of "X is Y" patterns
        m = re.search(r"(.+?)\s+\b(is|are|was|were)\b\s+(.+)", a.claim.text, re.IGNORECASE)
        if m:
            subj = m.group(1).strip()
            pred = m.group(3).strip().rstrip(".")
            stmt = f"If the claim is accurate, then {subj} has the attribute: {pred}."
            deds.append(
                Deduction(
                    statement=stmt,
                    from_claims=[idx],
                    assumptions=assumptions.copy(),
                    confidence=ConfidenceBand.LOW if a.confidence == ConfidenceBand.LOW else ConfidenceBand.MEDIUM,
                )
            )
    return deds


def build_epistemic_frame(
    input_text: str,
    context: Optional[Dict[str, Any]] = None,
    speaker: str = "user",
    max_claims: int = 20,
) -> EpistemicFrame:
    """
    Produce a frame from raw user text and optional upstream context.

    `context` can include:
      - "prior_claims": List[str] or List[Claim]
      - "topic": str
      - "time": str
      - "source_policy": dict
    """
    context = context or {}

    claims = extract_claims(input_text, speaker=speaker)[:max_claims]

    # Allow upstream claims to be included (optional)
    prior = context.get("prior_claims")
    if prior:
        if isinstance(prior, list) and prior and isinstance(prior[0], Claim):
            claims = prior + claims
        elif isinstance(prior, list) and prior and isinstance(prior[0], str):
            claims = [Claim(text=s, speaker="context") for s in prior] + claims

    assessments = assess_claims(claims)
    accepted, rejected, uncertain = _bucket(assessments)

    assumptions: List[str] = []
    # Baseline assumptions (explicit and safe)
    assumptions.append("User-provided statements are treated as claims unless independently supported.")
    if context.get("topic"):
        assumptions.append(f"Topic scope assumed: {context['topic']}")

    contradictions = _collect_contradictions(assessments)
    missing_context = _derive_missing_context(assessments)

    clarifying_questions = _build_clarifying_questions(assessments)

    # Verification steps: aggregate "needed_to_verify"
    verification_steps: List[str] = []
    for a in assessments:
        for need in a.needed_to_verify:
            if need not in verification_steps:
                verification_steps.append(need)

    # Deductions only from accepted claims (v1 conservative)
    deductions = _basic_deductions(accepted, assumptions)

    frame = EpistemicFrame(
        accepted=accepted,
        rejected=rejected,
        uncertain=uncertain,
        assumptions=assumptions,
        contradictions=contradictions,
        deductions=deductions,
        missing_context=missing_context,
        clarifying_questions=clarifying_questions,
        verification_steps=verification_steps,
        meta={
            "version": "0.1.0",
            "claims_extracted": len(claims),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "uncertain_count": len(uncertain),
        },
    )
    return frame


# ----------------------------
# Public API convenience
# ----------------------------

def run_epistemic_pipeline(
    user_text: str,
    context: Optional[Dict[str, Any]] = None,
) -> EpistemicFrame:
    """
    Convenience wrapper to align with "pipeline" naming.

    Example:
        frame = run_epistemic_pipeline(user_text, context={"topic": "medical claim"})
        logger.info("epistemic_frame=%s", frame.to_dict())
    """
    return build_epistemic_frame(user_text, context=context, speaker="user")


# ----------------------------
# Simple CLI test (optional)
# ----------------------------

if __name__ == "__main__":
    sample = """
    Nano-MIND technology can control brain circuits wirelessly.
    I read that it modulates emotions and appetite.
    This is definitely being used on me.
    https://example.com/some-article
    """

    frame = run_epistemic_pipeline(sample, context={"topic": "brain stimulation technology"})
    import json
    print(json.dumps(frame.to_dict(), indent=2))
