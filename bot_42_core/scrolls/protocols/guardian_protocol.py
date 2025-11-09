# Guardian Protocol — Core System

class GuardianProtocol:
    def __init__(self, citizen_id):
        self.citizen_id = citizen_id
        self.log = []

    def monitor_behavior(self, behavior_data):
        if self._detect_violation(behavior_data):
            return self._intervene()
        return "Stable"

    def _detect_violation(self, data):
        flags = ["harm", "cruelty", "deception", "self_destruction"]
        return any(flag in data.lower() for flag in flags)

    def _intervene(self):
        return "Intervention triggered: Support and restoration activated."

    def record_event(self, event):
        self.log.append(event)
        return f"Event recorded: {event}"
