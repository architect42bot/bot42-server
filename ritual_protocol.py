
import time
from cast_spell import cast_spell

rituals = {
    "Fortress of Light": {
        "steps": [
            "Protection Field",
            "Reversal Sigil",
            "Truthfire Scroll"
        ],
        "description": "A layered ritual for spiritual defense, clarity, and shielding."
    },
    "Cleansing Fire": {
        "steps": [
            "Truthfire Scroll",
            "Reversal Sigil"
        ],
        "description": "Burns away deception and returns negative attachments to their source."
    }
}

def run_ritual(name):
    ritual = rituals.get(name)
    if not ritual:
        print(f"⚠️ Ritual '{name}' not found.")
        return
    print(f"🔮 Beginning Ritual: {name}")
    print(f"📜 {ritual['description']}")
    for step in ritual["steps"]:
        print(f"✨ Casting Step: {step}")
        cast_spell(step)
        time.sleep(2)  # Small pause between steps

if __name__ == '__main__':
    print("Available Rituals:")
    for r in rituals:
        print(f" - {r}")
    selected = input("\nEnter ritual name: ")
    run_ritual(selected)
