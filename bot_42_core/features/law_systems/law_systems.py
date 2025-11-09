# new_law_system.py

from datetime import datetime
from typing import List, Dict, Optional

# -------------------------------
# Core Principles
# -------------------------------
PRINCIPLES = [
    "Equity and Fairness",
    "Restorative Justice",
    "Transparency and Accountability",
    "Flexibility",
    "Well-being and Sustainability"
]

# -------------------------------
# Rights Ledger
# -------------------------------
class Citizen:
    def __init__(self, name: str):
        self.name = name
        self.rights = ["Life", "Freedom", "Safety", "Education", "Health"]
        self.records = []  # Track conflicts, resolutions, and actions

    def add_record(self, record: Dict):
        self.records.append(record)

# -------------------------------
# Conflict Resolution
# -------------------------------
class Conflict:
    def __init__(self, parties: List[Citizen], description: str):
        self.parties = parties
        self.description = description
        self.status = "Open"
        self.resolution: Optional[str] = None
        self.created_at = datetime.now()
        self.resolved_at: Optional[datetime] = None

    def resolve(self, resolution: str):
        self.resolution = resolution
        self.status = "Resolved"
        self.resolved_at = datetime.now()
        # Record resolution for each party
        for party in self.parties:
            party.add_record({
                "conflict": self.description,
                "resolution": resolution,
                "timestamp": self.resolved_at
            })

# -------------------------------
# Adaptive Enforcement (Simplified)
# -------------------------------
class LawSystem:
    def __init__(self):
        self.citizens: Dict[str, Citizen] = {}
        self.conflicts: List[Conflict] = []

    def add_citizen(self, citizen: Citizen):
        self.citizens[citizen.name] = citizen

    def report_conflict(self, parties_names: List[str], description: str):
        parties = [self.citizens[name] for name in parties_names if name in self.citizens]
        conflict = Conflict(parties, description)
        self.conflicts.append(conflict)
        return conflict

    def resolve_conflict(self, conflict: Conflict, resolution: str):
        conflict.resolve(resolution)

    def get_citizen_records(self, name: str):
        citizen = self.citizens.get(name)
        return citizen.records if citizen else []

# -------------------------------
# Example Usage
# -------------------------------
if __name__ == "__main__":
    system = LawSystem()

    # Add citizens
    alice = Citizen("Alice")
    bob = Citizen("Bob")
    system.add_citizen(alice)
    system.add_citizen(bob)

    # Report a conflict
    conflict = system.report_conflict(["Alice", "Bob"], "Dispute over community resource")

    # Resolve conflict adaptively
    system.resolve_conflict(conflict, "Shared resource agreement and community service")

    # View records
    print(system.get_citizen_records("Alice"))
    print(system.get_citizen_records("Bob"))
