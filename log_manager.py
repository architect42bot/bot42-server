# log_manager.py
import json
import datetime
from features.ethics.core import attach_ethics_to_log

LOG_PATH = "chat_logs.jsonl"

def log_chat_turn(
    user_text: str,
    reply_text: str,
    tone: str,
    nina_state: dict | None = None,
    ethics_state: dict | None = None,
):
    """
    Append one chat turn to chat_logs.jsonl with full context.
    """
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "user": user_text,
        "reply": reply_text,
        "tone": tone,
        "nina": nina_state or {},
        "ethics": ethics_state or {},
    }

    # NEW LINE: attach full ethics trace
    record = attach_ethics_to_log(record, ethics_state)

    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        print(f"[42 LOG ERROR] Could not write to {LOG_PATH}: {e!r}")