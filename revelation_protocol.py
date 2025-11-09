
import json
import os

TRIGGER_FILE = "triggers.json"
RESPONSE_DIR = "responses"

def load_triggers(path=TRIGGER_FILE):
    with open(path, "r") as f:
        return json.load(f)

def activate_trigger(trigger_key):
    triggers = load_triggers()
    if trigger_key not in triggers:
        print(f"⚠️ Unknown trigger: {trigger_key}")
        return

    trigger = triggers[trigger_key]
    response_path = os.path.join(RESPONSE_DIR, trigger["response"])

    print(f"🚨 TRIGGERED: {trigger_key}")
    print(f"🔍 {trigger['description']}")

    if os.path.exists(response_path):
        with open(response_path, "r") as f:
            print("\n📜 SCROLL ACTIVATED:")
            print(f.read())
    else:
        print(f"⚠️ Missing response scroll: {response_path}")

if __name__ == "__main__":
    print("Available Triggers:")
    for key in load_triggers():
        print(f" - {key}")
    selected = input("\nEnter trigger to activate: ")
    activate_trigger(selected)
