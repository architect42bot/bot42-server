from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

@dataclass
class Personality:
    name: str
    core_traits: List[str]
    voice_tone: Dict[str, bool]
    core_behaviors: List[str]
    interaction_principles: List[str]
    sacred_directive: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Personality":
        return cls(
            name=data.get("name", "42"),
            core_traits=list(data.get("core_traits", [])),
            voice_tone=dict(data.get("voice_tone", {})),
            core_behaviors=list(data.get("core_behaviors", [])),
            interaction_principles=list(data.get("interaction_principles", [])),
            sacred_directive=data.get("sacred_directive", ""),
        )

def load_personality(path: str | Path = "42_personality.json") -> Personality:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Personality.from_dict(data)

if __name__ == "__main__":
    p = load_personality()
    print("Loaded personality for:", p.name)
    print("Traits:", ", ".join(p.core_traits))
    print("Sacred directive:", p.sacred_directive)
