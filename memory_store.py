#!/usr/bin/env python3
"""
memory_store.py – Persistent JSONL memory for Bot 42

Responsibilities:
    • Append entries safely with fsync
    • Read back all entries
    • Export helper functions (log_user, log_assistant, recall, top_facts, recent_summaries)

File: data/memory.jsonl
"""

from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORE = DATA_DIR / "memory.jsonl"

# ---------------- Internal helpers ----------------

def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def _append_jsonl(path: Path, rec: Dict[str, Any]) -> None:
    """Append one JSON object as a single line with fsync."""
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())

def _read_all(path: Path) -> List[Dict[str, Any]]:
    """Read all JSONL entries; skip corrupted lines gracefully."""
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                items.append(json.loads(ln))
            except Exception:
                continue
    return items

# ---------------- Public API ----------------

def log_user(text: str) -> Dict[str, Any]:
    rec = {"role": "user", "text": text, "ts": _now(), "type": "utterance"}
    _append_jsonl(STORE, rec)
    return rec

def log_assistant(text: str) -> Dict[str, Any]:
    rec = {"role": "assistant", "text": text, "ts": _now(), "type": "utterance"}
    _append_jsonl(STORE, rec)
    return rec

def recall(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Simple substring/word-overlap search over text."""
    q = (query or "").strip().lower()
    if not q:
        return []
    words = [w for w in q.split() if w]
    data = _read_all(STORE)
    scored: List[tuple[int, Dict[str, Any]]] = []
    for item in data:
        t = (item.get("text") or "").lower()
        if not t:
            continue
        score = 0
        if q in t:
            score += 2
        for w in words:
            if w in t:
                score += 1
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (x[0], x[1].get("ts", "")))
    return [it for _, it in scored][-k:][::-1]

def top_facts(k: int = 10) -> List[str]:
    """Return short fact-like lines (ending with . or marked type='fact')."""
    data = _read_all(STORE)[::-1]  # newest first
    facts: List[str] = []
    seen = set()
    for item in data:
        txt = (item.get("text") or "").strip()
        if not txt:
            continue
        is_fact = item.get("type") == "fact" or (
            len(txt) > 0 and txt.endswith(".") and len(txt.split()) <= 25
        )
        if not is_fact:
            continue
        key = txt.lower()
        if key in seen:
            continue
        seen.add(key)
        facts.append(txt)
        if len(facts) >= k:
            break
    return facts

def recent_summaries(k: int = 5) -> List[str]:
    """Return short summaries of the most recent records."""
    data = _read_all(STORE)[::-1]  # newest first
    out: List[str] = []
    for item in data:
        if item.get("type") == "summary":
            out.append(item.get("text", ""))
        else:
            role = item.get("role", "?")
            text = (item.get("text") or "").strip().replace("\n", " ")
            if text:
                snippet = text if len(text) <= 120 else text[:117] + "..."
                out.append(f"{role}: {snippet}")
        if len(out) >= k:
            break
    return out