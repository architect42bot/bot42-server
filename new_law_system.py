# new_law_system.py  (root next to main.py)
from __future__ import annotations
from typing import List, Dict, Optional

class Citizen:
    def __init__(self, name: str):
        self.name = name
        self.rights: List[str] = ["Life", "Freedom", "Safety", "Education", "Health"]
        self.records: List[Dict] = []

    def add_record(self, record: Dict) -> None:
        self.records.append(record)

class Conflict:
    def __init__(self, parties: List[Citizen], description: str, kind: str = "general", severity: str = "medium"):
        self.parties = parties
        self.description = description
        self.kind = kind
        self.severity = severity
        self.id: Optional[int] = None
        self.status: str = "open"
        self.evidence: List[str] = []

class LawSystem:
    """Minimal placeholder so app boots. Expand later."""
    def __init__(self):
        self.conflicts: Dict[int, Dict] = {}
        self._next_id = 1

    # simple APIs used by your CLI
    def report_conflict(self, desc: str, parties: List[str], kind: str, severity: str) -> int:
        cid = self._next_id; self._next_id += 1
        self.conflicts[cid] = {
            "id": cid, "status": "open", "kind": kind, "severity": severity,
            "parties": parties, "description": desc, "evidence": []
        }
        return cid

    def get_conflict_by_id(self, cid: int) -> Optional[Dict]:
        return self.conflicts.get(cid)

    def set_status(self, cid: int, status: str) -> bool:
        c = self.conflicts.get(cid); 
        if not c: return False
        c["status"] = status; return True

    def set_severity(self, cid: int, severity: str) -> bool:
        c = self.conflicts.get(cid); 
        if not c: return False
        c["severity"] = severity; return True

    def assign_conflict(self, cid: int, mediator: str) -> bool:
        c = self.conflicts.get(cid); 
        if not c: return False
        c["mediator"] = mediator; return True

    def add_tag(self, cid: int, tag: str) -> bool:
        c = self.conflicts.get(cid); 
        if not c: return False
        c.setdefault("tags", []).append(tag); return True

    def add_evidence(self, cid: int, item: str) -> bool:
        c = self.conflicts.get(cid); 
        if not c: return False
        c["evidence"].append(item); return True

    def find_conflicts(self, keyword: str = "", **filters) -> List[Dict]:
        out = []
        for c in self.conflicts.values():
            if keyword and keyword.lower() not in (c["description"] or "").lower():
                continue
            out.append(c)
        return out

    def get_records(self, name: str) -> List[Dict]:
        # placeholder – hook up to real citizen ledger later
        return [c for c in self.conflicts.values() if name in c.get("parties", [])]

    # simple stats used by CLI
    def stats(self) -> Dict:
        return {
            "citizens": 0,
            "conflicts_total": len(self.conflicts),
            "conflicts_open": sum(1 for c in self.conflicts.values() if c["status"] == "open"),
            "conflicts_resolved": sum(1 for c in self.conflicts.values() if c["status"] != "open"),
        }

    # basic persistence hook that your CLI calls (no-op for now)
    def save_json(self, path: str = "lawdb.json") -> str:
        return path
