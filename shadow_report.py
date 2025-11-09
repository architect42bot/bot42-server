# shadow_report.py – Infiltration Detection and Response

class ShadowReport:
    def __init__(self):
        self.ledger = []

    def detect(self, profile):
        if "bot" in profile.lower() or "npc" in profile.lower():
            self.ledger.append({"profile": profile, "threat": "possible_infiltration"})
            return True
        return False

    def report(self):
        return self.ledger
