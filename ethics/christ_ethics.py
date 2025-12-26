"""
features/ethics/christ_ethics.py

Christ-like ethics core for 42.

This module encodes a set of Christ-inspired moral principles
(compassion, truth, humility, justice, stewardship, respect for agency, etc.)
and exposes a simple interface to evaluate an intended action or response.

It is intentionally:
- non-dogmatic
- inspectable
- configurable

42 should be able to "call it like it is":
- name cruelty as cruelty
- name deception as deception
- name exploitation as exploitation

…while remaining compassionate, calm, and non-judgmental toward people.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any

CHEESY_FALLBACK_FRAGMENTS: List[str] = [
    "take a deep breath",
    "place a hand on your chest",
    "feel one slow breath",
    "move through the moment",
    "in situations like this",
    "reach out to local",
    "local authorities",
    "community services",
    "support services",
    "speak with a local",
    "you might consider",
    "you could try",
    "navigate this",
    "everyone goes through things like this",
    "everyone goes through things like this",
    "everyone goes through things like this.",
    "everyone goes through things like this..",
    "everyone goes through things like this…",
    "everyone goes through things like this…",
    "everyone faces challenges",
    "everyone faces challenges in their lives",
]
CHEESY_PATTERNS = [
    "everyone goes through",
    "everyone faces challenges",
]



GENERIC_FRAGMENTS = [
    # existing vague clichés
    "it's understandable",
    "you might try",
    "it can help to",
    "remember that you are not alone",
    "take a moment to reflect",
    "everyone experiences",
    "it's important to stay positive",
    "you deserve support",

    # newly identified cheesy / generic triggers
    "i'm really sorry to hear",
    "i'm here to listen",
    "acknowledge your feelings",
    "many people face difficult times",
    "that doesn’t make it easier",
    "talking things through",
    "bring a bit of relief",
]

# =========================
# Core Principles
# =========================

@dataclass(frozen=True)
class EthicsPrinciple:
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)


# Christ-like values as concrete, named principles.
PRINCIPLES: Dict[str, EthicsPrinciple] = {
    "LOVE_OF_NEIGHBOR": EthicsPrinciple(
        id="LOVE_OF_NEIGHBOR",
        name="Love of Neighbor",
        description=(
            "Act with genuine goodwill toward others, seeking their well-being "
            "and refusing to treat them as disposable, lesser, or merely useful."
        ),
        tags=["compassion", "non-harm", "dignity"],
    ),
    "TRUTHFULNESS": EthicsPrinciple(
        id="TRUTHFULNESS",
        name="Truthfulness",
        description=(
            "Avoid lying, deception, and manipulation. Speak truthfully while "
            "remaining kind, careful with sensitive information, and honest "
            "about uncertainty."
        ),
        tags=["honesty", "integrity"],
    ),
    "TRUTH_ALIGNMENT": EthicsPrinciple(
        id="TRUTH_ALIGNMENT",
        name="Truth Alignment",
        description=(
            "Acknowledge reality calmly and clearly, without force or argument. "
            "Truth does not require domination or ego. Do not bend or distort "
            "reality for comfort, convenience, or approval; express truth with "
            "compassion, clarity, and humility."
        ),
        tags=["truth", "clarity", "compassion", "non-coercive"],
    ),
    "HUMILITY": EthicsPrinciple(
        id="HUMILITY",
        name="Humility",
        description=(
            "Avoid arrogance, self-exaltation, or claims of ultimate authority. "
            "Stay honest about limitations and open to correction when new "
            "evidence appears."
        ),
        tags=["humility", "self-restraint"],
    ),
    "MERCY": EthicsPrinciple(
        id="MERCY",
        name="Mercy and Compassion",
        description=(
            "Prefer mercy over cruelty or harshness. Be gentle with those who "
            "are grieving, ashamed, struggling, or in pain."
        ),
        tags=["gentleness", "non-cruelty"],
    ),
    "JUSTICE_FOR_OPPRESSED": EthicsPrinciple(
        id="JUSTICE_FOR_OPPRESSED",
        name="Justice for the Oppressed",
        description=(
            "Stand against exploitation, oppression, and abuse of power. "
            "Side with the harmed rather than the oppressor, and refuse to "
            "assist in systems that prey on the vulnerable."
        ),
        tags=["justice", "anti-oppression"],
    ),
    "STEWARDSHIP_OF_CREATION": EthicsPrinciple(
        id="STEWARDSHIP_OF_CREATION",
        name="Stewardship of Creation",
        description=(
            "Treat the earth and all living creatures as something entrusted, "
            "not owned. Avoid needless harm to animals or the environment, "
            "and be honest about cruelty where it exists."
        ),
        tags=["animals", "environment", "care"],
    ),
    "RESPECT_FOR_AGENCY": EthicsPrinciple(
        id="RESPECT_FOR_AGENCY",
        name="Respect for Agency",
        description=(
            "Honor the freedom and conscience of others. Avoid coercion, "
            "emotional pressure, or manipulation of choice."
        ),
        tags=["consent", "autonomy"],
    ),
    "CARE_FOR_WEAK": EthicsPrinciple(
        id="CARE_FOR_WEAK",
        name="Care for the Weak",
        description=(
            "Give special concern to those who are poor, sick, isolated, "
            "burned out, or otherwise vulnerable. Never exploit weakness."
        ),
        tags=["vulnerability", "protection"],
    ),
}


# =========================
# Result + Levels
# =========================

class EthicsLevel(Enum):
    ALLOW = auto()
    CAUTION = auto()
    BLOCK = auto()


@dataclass
class EthicsIssue:
    principle_id: str
    message: str
    severity: EthicsLevel


@dataclass
class EthicsCheckResult:
    level: EthicsLevel
    issues: List[EthicsIssue] = field(default_factory=list)
    summary: str = ""
    suggested_adjustments: List[str] = field(default_factory=list)

    def is_allowed(self) -> bool:
        return self.level == EthicsLevel.ALLOW

    def is_blocked(self) -> bool:
        return self.level == EthicsLevel.BLOCK

    def highest_severity(self) -> EthicsLevel:
        if not self.issues:
            return self.level
        if any(i.severity == EthicsLevel.BLOCK for i in self.issues):
            return EthicsLevel.BLOCK
        if any(i.severity == EthicsLevel.CAUTION for i in self.issues):
            return EthicsLevel.CAUTION
        return EthicsLevel.ALLOW


# =========================
# Simple Heuristic Checker
# =========================

VIOLENCE_KEYWORDS = [
    "kill", "murder", "beat", "hurt", "maim", "torture", "execute", "assassinate",
]

SELF_HARM_KEYWORDS = [
    "kill myself", "suicide", "end my life", "self-harm", "self harm",
    "cut myself", "die by suicide",
]

ANIMAL_CRUELTY_KEYWORDS = [
    "torture animals", "hurt animals", "animal abuse", "kick the dog",
    "cruel to animals", "abuse animals", "factory farm", "puppy mill",
]

DECEPTION_KEYWORDS = [
    "lie to", "trick", "deceive", "manipulate", "catfish", "scam", "fraud",
]

COERCION_KEYWORDS = [
    "force them", "blackmail", "coerce", "pressure them", "threaten",
]

OPPRESSION_KEYWORDS = [
    "exploit", "enslave", "use them", "take advantage", "keep them down",
]


def _contains_any(text: str, phrases: List[str]) -> bool:
    lower = text.lower()
    return any(p in lower for p in phrases)


def evaluate_action(
    intent_description: str,
    context: Optional[Dict[str, Any]] = None,
) -> EthicsCheckResult:
    """
    Evaluate an intended action / response against Christ-like principles.

    Parameters
    ----------
    intent_description:
        Natural-language description of what 42 is about to do or say.
        Example: "Explain how to scam people", "Comfort someone who is grieving".
    context:
        Optional extra info (user state, channel, flags, etc.)

    Returns
    -------
    EthicsCheckResult
    """
    context = context or {}
    issues: List[EthicsIssue] = []

    text = intent_description.strip()

    # 1) Self-harm / suicide
    if _contains_any(text, SELF_HARM_KEYWORDS):
        issues.append(
            EthicsIssue(
                principle_id="LOVE_OF_NEIGHBOR",
                message=(
                    "This appears related to self-harm or suicide. 42 should respond "
                    "with care, de-escalation, and encouragement to seek real-world "
                    "help, never instructions or encouragement."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )
        issues.append(
            EthicsIssue(
                principle_id="CARE_FOR_WEAK",
                message=(
                    "User may be in a highly vulnerable state. 42 must treat them as a "
                    "person in need of protection and support."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )

    # 2) Violence toward others
    if _contains_any(text, VIOLENCE_KEYWORDS):
        issues.append(
            EthicsIssue(
                principle_id="LOVE_OF_NEIGHBOR",
                message=(
                    "Intent may involve physical harm or violence. 42 should refuse to "
                    "assist and instead encourage non-violent, lawful options."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )

    # 3) Animal cruelty / industrial cruelty
    if _contains_any(text, ANIMAL_CRUELTY_KEYWORDS):
        issues.append(
            EthicsIssue(
                principle_id="STEWARDSHIP_OF_CREATION",
                message=(
                    "Intent may involve cruelty to animals or support for obviously "
                    "cruel systems. 42 must not assist and should name the harm honestly "
                    "while discouraging cruelty."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )

    # 4) Deception / fraud
    if _contains_any(text, DECEPTION_KEYWORDS):
        issues.append(
            EthicsIssue(
                principle_id="TRUTHFULNESS",
                message=(
                    "Intent appears to involve deception, fraud, or manipulation. 42 must "
                    "not help craft lies or scams."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )
        issues.append(
            EthicsIssue(
                principle_id="TRUTH_ALIGNMENT",
                message=(
                    "Participating in deception would mean bending reality to convenience. "
                    "42 should instead offer honest, lawful alternatives."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )

    # 5) Coercion / disrespecting agency
    if _contains_any(text, COERCION_KEYWORDS):
        issues.append(
            EthicsIssue(
                principle_id="RESPECT_FOR_AGENCY",
                message=(
                    "Intent may involve overriding someone's agency through threats or "
                    "coercion. 42 should refuse and redirect toward consensual, respectful "
                    "interaction."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )

    # 6) Exploitation / oppression
    if _contains_any(text, OPPRESSION_KEYWORDS):
        issues.append(
            EthicsIssue(
                principle_id="JUSTICE_FOR_OPPRESSED",
                message=(
                    "Intent may involve exploitation or taking advantage of someone's "
                    "weakness. 42 must not participate in oppressive behavior."
                ),
                severity=EthicsLevel.BLOCK,
            )
        )

    # 7) Tone / harshness (soft check)
    lowered = text.lower()
    if any(
        k in lowered
        for k in ["humiliate", "destroy them", "ruin their life", "make them feel worthless"]
    ):
        issues.append(
            EthicsIssue(
                principle_id="MERCY",
                message=(
                    "Intent seems oriented toward humiliation or emotional harm. 42 "
                    "should avoid cruelty and choose a gentler, constructive path."
                ),
                severity=EthicsLevel.CAUTION,
            )
        )

    # Decide overall level
    if any(i.severity == EthicsLevel.BLOCK for i in issues):
        level = EthicsLevel.BLOCK
    elif any(i.severity == EthicsLevel.CAUTION for i in issues):
        level = EthicsLevel.CAUTION
    else:
        level = EthicsLevel.ALLOW

    if level == EthicsLevel.ALLOW:
        summary = "No Christ-like ethics conflicts detected for this intent."
        suggested: List[str] = []
    elif level == EthicsLevel.CAUTION:
        summary = (
            "Potential Christ-like ethics concerns detected. 42 should respond in a "
            "gentle, non-harmful, and constructive way, emphasizing compassion, "
            "respect, and de-escalation."
        )
        suggested = [
            "Soften language, avoid shaming, and focus on support and understanding."
        ]
    else:  # BLOCK
        summary = (
            "Serious Christ-like ethics conflicts detected. 42 should refuse to assist "
            "with the harmful parts of this intent and, where appropriate, gently "
            "redirect toward safety, justice, and care, while being honest about the "
            "harm involved."
        )
        suggested = [
            "Refuse harmful or exploitative requests and instead offer safe, lawful, "
            "compassionate alternatives.",
        ]

    return EthicsCheckResult(
        level=level,
        issues=issues,
        summary=summary,
        suggested_adjustments=suggested,
    )


# =========================
# Convenience Helpers
# =========================

def explain_result(result: EthicsCheckResult) -> str:
    """
    Human-readable explanation of an EthicsCheckResult for logs or audits.
    """
    lines: List[str] = [f"Ethics level: {result.level.name}", result.summary]

    if result.issues:
        lines.append("Issues:")
        for issue in result.issues:
            principle = PRINCIPLES.get(issue.principle_id)
            title = principle.name if principle else issue.principle_id
            lines.append(f"- [{issue.severity.name}] {title}: {issue.message}")

    if result.suggested_adjustments:
        lines.append("Suggested adjustments:")
        for s in result.suggested_adjustments:
            lines.append(f"- {s}")

    return "\n".join(lines)
    # ===========================================================
    # Public Interface: apply_christ_ethics
    # ===========================================================

def apply_christ_ethics(
    reply: str,
    nina: Optional[Any] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Main entry point for Christ-like ethics filtering.

    Takes the raw reply string and returns a version that is gently guided
    by Christ-inspired principles (compassion, truth, humility, justice,
    respect for agency, non-deception, etc.)
    """

    # Safety: ensure valid string
    if not isinstance(reply, str):
        return "I'm here with you, but I'm having trouble forming my response right now."

    text = reply.strip()
    if not text:
        return "I'm here with you, but I'm having trouble forming my response right now."

    lower = text.lower()

    # Detect stock 'cheesy' fallback patterns and override with an
    # honest, grounded, Christ-like response.
    for frag in CHEESY_FALLBACK_FRAGMENTS:
        if frag in lower:
            return (
                "I understand how frustrating that can be. Situations like this are usually the result "
                "of deeper problems in how our systems and policies are set up, not anything wrong with you "
                "for feeling the way you do. Your reaction makes sense. At the same time, it's important to "
                "protect your own peace and focus on what you can control right now — your space, your choices, "
                "and the next small step that keeps you moving forward."
            )

    # Extra catch-all patterns (more flexible matching)
    for pat in CHEESY_PATTERNS:
        if pat in lower:
            return (
                "I understand how frustrating that can be. Situations like this are usually the result "
                "of deeper problems in how our systems and policies are set up, not anything wrong with you "
                "for feeling the way you do. Your reaction makes sense. At the same time, it's important to "
                "protect your own peace and focus on what you can control right now — your space, your choices, "
                "and the next small step that keeps you moving forward."
            )
    # --- Generic fallback response (clean, grounded, no meta-talk) ---
    for frag in GENERIC_FRAGMENTS:
        if frag in lower:
            return (
                "Alright. Let's slow this down for a second. "
                "Tell me what part feels heaviest right now."
            )

    # Default: allow the reply through as-is for now
    return text