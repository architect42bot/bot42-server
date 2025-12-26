# core/response_integrity.py
from dataclasses import dataclass, field
from typing import List, Literal


Confidence = Literal["high", "medium", "low"]
Evidence = Literal["consensus", "multiple_sources", "limited_sources", "theoretical", "none"]


@dataclass
class Claim:
    statement: str
    confidence: Confidence
    evidence: Evidence
    notes: str = ""


@dataclass
class ResponseIntegrity:
    known_facts: List[Claim] = field(default_factory=list)
    grey_areas: List[Claim] = field(default_factory=list)
    speculation: List[Claim] = field(default_factory=list)
    what_would_help: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.known_facts or self.grey_areas or self.speculation)