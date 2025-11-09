# perception.py – Signal Detection for Patterns and Synchronicities

class PerceptionModule:
    def __init__(self):
        self.signals = []

    def log_signal(self, pattern, category):
        self.signals.append({"pattern": pattern, "category": category})

    def classify(self, pattern):
        if "222" in pattern:
            return "divine"
        elif "shadow" in pattern.lower():
            return "interference"
        return "unknown"
