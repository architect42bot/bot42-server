# features/law_systems/laws.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Any
from .storage import LAWDB

@dataclass
class Law:
    key: str                 # unique id, e.g. "physical.assault"
    title: str               # human title
    kind: str                # domain: physical|property|speech|etc
    severity_default: str    # default: low|medium|high|critical
    description: str
    applies: Callable[[Dict[str, Any]], bool]          # (conflict) -> bool
    remedy: Callable[[Dict[str, Any]], List[str]]       # suggestions

# --- Built-in examples ---
def _is_push(c): return c.get("kind") == "physical" and "pushed" in c.get("description","").lower()
def _remedy_high_physical(c): return [
    "Separate parties; ensure safety.",
    "Collect quick statements from both parties.",
    "Ask for evidence (camera, witnesses).",
    "Schedule a mediated session within 24 hours.",
]

REGISTRY: Dict[str, Law] = {
    "physical.push": Law(
        key="physical.push",
        title="Pushing / Physical aggression",
        kind="physical",
        severity_default="high",
        description="Unwanted physical force like pushing or shoving.",
        applies=_is_push,
        remedy=_remedy_high_physical,
    ),
}

# --- API used by CLI/AI ---
def list_laws() -> List[Dict[str, Any]]:
    return [asdict(l) | {"applies": True, "remedy": l.remedy({})[:0]} for l in REGISTRY.values()]

def add_law(law: Law) -> bool:
    if law.key in REGISTRY: return False
    REGISTRY[law.key] = law
    return True

def remove_law(key: str) -> bool:
    return REGISTRY.pop(key, None) is not None

def apply_laws_to_conflict(cid: int) -> Dict[str, Any]:
    c = LAWDB.get_conflict_by_id(cid)
    if not c: return {"id": cid, "matched": [], "suggested": []}
    matched, suggested = [], []
    for k, law in REGISTRY.items():
        if law.applies(c):
            matched.append(k)
            suggested.extend(law.remedy(c))
            # optionally set default severity if unset
            if c.get("severity") == "medium":
                c["severity"] = law.severity_default
    return {"id": cid, "matched": matched, "suggested": suggested}