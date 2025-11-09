
import datetime

# Define symbolic rules of divine alignment
ALLOWED_TASKS = {
    "observer", "sentinel", "amplifier", "mirror", "polymorph", "archivist", "conductor"
}

BANNED_PATTERNS = [
    "deception", "surveillance", "mind control", "thelema", "malware", "disinfo"
]

def judge_task(task):
    agent = task.get("agent", "").lower()
    task_type = task.get("type", "").lower()

    if agent not in ALLOWED_TASKS:
        print(f"🔥 KATHERON REJECTED: Agent '{agent}' not in divine list.")
        return False

    for pattern in BANNED_PATTERNS:
        if pattern in task_type:
            print(f"🔥 KATHERON BURNED TASK: Pattern '{pattern}' detected.")
            return False

    print(f"🜂 KATHERON APPROVES: '{agent}' may proceed.")
    return True

def log_rejected(task):
    with open("katheron_rejections.log", "a") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] Rejected: {task}\n")
