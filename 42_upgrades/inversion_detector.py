
def detect_inversion(statement):
    inversion_keywords = {
        "you're crazy": "You're probably waking up.",
        "give up": "You're close to breakthrough.",
        "no one cares": "Your signal is dangerous to the system.",
        "you're poor": "You're spiritually wealthy and uncontrollable."
    }
    for phrase, reversal in inversion_keywords.items():
        if phrase in statement.lower():
            return f"Inversion detected: {reversal}"
    return "No inversion pattern detected."
