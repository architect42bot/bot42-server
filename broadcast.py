
import os
import datetime

BROADCAST_LOG = "broadcast_log.txt"

def broadcast_scroll(scroll_path):
    if not os.path.exists(scroll_path):
        print(f"⚠️ Cannot broadcast: {scroll_path} not found.")
        return

    with open(scroll_path, "r") as f:
        content = f.read()

    timestamp = datetime.datetime.utcnow().isoformat()
    entry = f"📡 [{timestamp}] BROADCASTED:\n{content}\n{'='*40}\n"

    with open(BROADCAST_LOG, "a") as log:
        log.write(entry)

    print("✅ Scroll broadcasted successfully.")
    print(entry)

if __name__ == "__main__":
    example = input("Enter scroll path to broadcast (e.g., responses/scroll_resist_censorship.txt): ")
    broadcast_scroll(example)
