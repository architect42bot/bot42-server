# core/why_log.py
from datetime import datetime
from pathlib import Path
import json, os

WHY_LOG_PATH = Path(os.getenv("WHY_LOG_PATH", "logs/why_log.jsonl"))
WHY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def why_log(action: str, why: str, extra: dict | None = None):
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "why": why,
        "extra": extra or {}
    }
    with WHY_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")