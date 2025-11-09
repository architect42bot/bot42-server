# features/law_systems/storage.py
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Any


DB_DEFAULT_PATH = "lawdb.json"


class LawDB:
    """
    Simple in-memory database for the law system.
    - citizens: dict keyed by citizen name
    - conflicts: list of conflict dicts
    - next_id: incremental id for conflicts
    """

    def __init__(self) -> None:
        self.citizens: Dict[str, Dict[str, Any]] = {}
        self.conflicts: List[Dict[str, Any]] = []
        self.next_id: int = 1

    # ---------- Citizen helpers ----------
    def add_citizen(self, name: str) -> bool:
        """Add a citizen if not present. Returns True if added, False if exists."""
        if not name:
            return False
        if name in self.citizens:
            return False
        self.citizens[name] = {"name": name}
        return True

    def get_records(self, name: str) -> List[Dict[str, Any]]:
        """
        Return conflict records for a given citizen by scanning conflicts where
        the citizen appears in 'parties'.
        """
        out: List[Dict[str, Any]] = []
        for c in self.conflicts:
            if name in c.get("parties", []):
                out.append(
                    {
                        "id": c.get("id"),
                        "description": c.get("description", ""),
                        "status": c.get("status", "open"),
                        "severity": c.get("severity", "medium"),
                        "kind": c.get("kind", "physical"),
                        "tags": list(c.get("tags", [])),
                        "assigned_to": c.get("assigned_to"),
                    }
                )
        return out

    # ---------- Internal utilities ----------
    def _ensure_id(self) -> int:
        nid = int(self.next_id or 1)
        self.next_id = nid + 1
        return nid

    def get_conflict_by_id(self, cid: int) -> Optional[Dict[str, Any]]:
        for c in self.conflicts:
            if c.get("id") == cid:
                return c
        return None

    # ---------- Create / mutate conflicts ----------
    def report_conflict(
        self,
        description: str,
        parties: Optional[List[str]] = None,
        kind: str = "physical",
        severity: str = "medium",
    ) -> int:
        """Create a conflict and return its id."""
        parties = parties or []
        # Ensure citizens exist
        for p in parties:
            self.add_citizen(p)

        conflict = {
            "id": self._ensure_id(),
            "description": description,
            "status": "open",                 # open | resolved | dismissed
            "kind": kind,                     # 'physical', etc.
            "severity": severity,             # low | medium | high | critical
            "parties": parties,               # e.g., ["Alice", "Bob"]
            "assigned_to": None,              # mediator/owner
            "evidence": [],                   # list[str]
            "tags": [],                       # list[str]
            "notes": [],                      # list[{"by","note"}]
            "timeline": [{"event": "create"}] # audit trail
        }
        self.conflicts.append(conflict)
        return conflict["id"]

    def set_status(self, cid: int, status: str) -> bool:
        c = self.get_conflict_by_id(cid)
        if not c:
            return False
        c["status"] = status
        c.setdefault("timeline", []).append({"event": "status", "to": status})
        return True

    def set_severity(self, cid: int, severity: str) -> bool:
        c = self.get_conflict_by_id(cid)
        if not c:
            return False
        c["severity"] = severity
        c.setdefault("timeline", []).append({"event": "severity", "to": severity})
        return True

    def assign_conflict(self, cid: int, mediator: str) -> bool:
        c = self.get_conflict_by_id(cid)
        if not c:
            return False
        c["assigned_to"] = mediator
        c.setdefault("timeline", []).append({"event": "assign", "to": mediator})
        return True

    def add_tag(self, cid: int, tag: str) -> bool:
        c = self.get_conflict_by_id(cid)
        if not c:
            return False
        tags = c.setdefault("tags", [])
        if tag not in tags:
            tags.append(tag)
            c.setdefault("timeline", []).append({"event": "tag", "tag": tag})
        return True

    def add_evidence(self, cid: int, item: str) -> bool:
        c = self.get_conflict_by_id(cid)
        if not c:
            return False
        c.setdefault("evidence", []).append(item)
        c.setdefault("timeline", []).append({"event": "evidence"})
        return True

    def add_note(self, cid: int, note: str, by: str = "system") -> bool:
        c = self.get_conflict_by_id(cid)
        if not c:
            return False
        c.setdefault("notes", []).append({"by": by, "note": note})
        c.setdefault("timeline", []).append({"event": "note", "by": by})
        return True

    def delete_conflict(self, cid: int) -> bool:
        before = len(self.conflicts)
        self.conflicts = [c for c in self.conflicts if c.get("id") != cid]
        return len(self.conflicts) < before

    # ---------- Queries ----------
    def find_conflicts(
        self,
        keyword: str = "",
        status: Optional[str] = None,
        tag: Optional[str] = None,
        party: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = self.conflicts
        if keyword:
            kw = keyword.lower()
            results = [c for c in results if kw in c.get("description", "").lower()]
        if status:
            results = [c for c in results if c.get("status") == status]
        if tag:
            results = [c for c in results if tag in c.get("tags", [])]
        if party:
            results = [c for c in results if party in c.get("parties", [])]
        if kind:
            results = [c for c in results if c.get("kind") == kind]
        return results

    # ---------- Stats ----------
    def stats(self) -> Dict[str, int]:
        total = len(self.conflicts)
        resolved = sum(1 for c in self.conflicts if c.get("status") == "resolved")
        open_ = total - resolved
        return {
            "citizens": len(self.citizens),
            "conflicts_total": total,
            "conflicts_open": open_,
            "conflicts_resolved": resolved,
        }

    # ---------- Persistence ----------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "citizens": self.citizens,
            "conflicts": self.conflicts,
            "meta": {"next_id": self.next_id},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LawDB":
        db = cls()
        db.citizens = data.get("citizens", {})
        db.conflicts = data.get("conflicts", [])
        db.next_id = data.get("meta", {}).get("next_id", 1)
        return db

    def save_json(self, path: str = DB_DEFAULT_PATH) -> str:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return os.path.abspath(path)

    @classmethod
    def load_json(cls, path: str = DB_DEFAULT_PATH) -> "LawDB":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ----------------------------
# Shared database instance
# ----------------------------
# Auto-load from disk if a DB file exists; otherwise start fresh.
try:
    _DEFAULT_PATH = os.environ.get("LAWDB_PATH", DB_DEFAULT_PATH)
    if os.path.exists(_DEFAULT_PATH):
        LAWDB = LawDB.load_json(_DEFAULT_PATH)
    else:
        LAWDB = LawDB()
except Exception:
    # Fallback to an empty DB if anything goes wrong during import.
    LAWDB = LawDB()