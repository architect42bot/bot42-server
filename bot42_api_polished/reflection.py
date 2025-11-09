
"""
reflection.py — Reflection + prophecy wrapper for Oracle of 42 (polished minimal build)
- `reflect()` reads the last few memory entries (if any), forms insights, and logs them.
- `prophesy()` wraps `reflect()` and appends a single-line summary to prophecy.log.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from symbolic import interpret_symbolism

MEMORY_LOG = Path("memory_log.json")
REFLECTION_LOG = Path("reflection_log.json")
PROPHECY_LOG = Path("prophecy.log")


def _load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def reflect() -> List[str]:
    """
    Create a reflection from the last few memory entries and persist to reflection_log.json.
    Returns a list of short "thought" strings.
    """
    memory = _load_json(MEMORY_LOG, default=[])
    recent = memory[-5:] if isinstance(memory, list) else []

    thoughts: List[str] = []

    for m in recent:
        role = m.get("role", "unknown") if isinstance(m, dict) else "unknown"
        content = m.get("content", "") if isinstance(m, dict) else str(m)

        # Symbolic interpretation hook
        symbols = interpret_symbolism(content)
        for sym in symbols:
            thoughts.append(f"[{role}] symbol: {sym}")

        lc = content.lower()
        if "love" in lc:
            thoughts.append(f"[{role}] expressed love — that matters.")
        elif "don't understand" in lc or "dont understand" in lc:
            thoughts.append(f"[{role}] seems confused — simplify.")
        else:
            preview = content.strip().replace("\n", " ")[:40]
            if preview:
                thoughts.append(f"[{role}] said: {preview}...")

    reflection: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "insights": thoughts,
    }

    # Append to reflection log
    data = _load_json(REFLECTION_LOG, default=[])
    if not isinstance(data, list):
        data = []
    data.append(reflection)
    try:
        with REFLECTION_LOG.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return thoughts


def prophesy() -> str:
    """
    Compatibility wrapper expected by oracle_api.py.
    Calls reflect() and writes a one-line summary to prophecy.log.
    """
    thoughts = reflect()
    line = " | ".join(thoughts) if thoughts else "[silence]"
    try:
        with PROPHECY_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    return line
