#!/usr/bin/env python3
"""
reflection.py — lightweight reflection engine for Bot 42 (stdlib only)

What it does
------------
• Scans the most recent user/assistant utterances from data/memory.jsonl
• Extracts fact-like statements via simple regex patterns:
    - identity   (e.g., "I am X", "I'm X")
    - location   (e.g., "I am in X", "I live in X")
    - need       (e.g., "I need X", "I could use X")
    - preference (e.g., "I like X", "I love X")
    - generic declarative facts ending with a period (short)
• Appends deduplicated results as records with type="fact"
• Adds a small rolling summary with type="summary"
• Never throws from the public API; returns a result dict.

Public API
----------
- class Reflector(...):
    .maybe_reflect() -> dict

- function maybe_reflect() -> dict
  (uses a default Reflector instance)

Tuneables
---------
reflect_every   : run only if at least this many new utterances since last reflect
max_ctx         : max utterances to scan (newest-first)
"""

from __future__ import annotations
import json, os, re, time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Store path (shared with memory_store.py)
DATA_DIR = Path("data")
STORE = DATA_DIR / "memory.jsonl"
META  = DATA_DIR / "reflection.meta.json"  # to remember last_reflected_index

# ---------- Utilities shared with memory_store style ----------

def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def _append_jsonl(path: Path, rec: Dict[str, Any]) -> None:
    """Append one JSON object as a single line with fsync (no external deps)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())

def _read_all(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, ln in enumerate(f):
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                obj["_idx"] = i  # keep a running index to track progress
                items.append(obj)
            except Exception:
                continue
    return items

def _load_meta() -> Dict[str, Any]:
    if META.exists():
        try:
            return json.loads(META.read_text("utf-8"))
        except Exception:
            pass
    return {"last_reflected_idx": -1}

def _save_meta(meta: Dict[str, Any]) -> None:
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- Extraction patterns ----------

_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    # name, compiled regex
    ("identity",  re.compile(r"\b(i\s+am|i'm)\s+(?P<x>[^.?!,;]+)", re.I)),
    ("location",  re.compile(r"\b(i\s*(am|’m)\s*in|i\s*live\s*in)\s+(?P<x>[^.?!,;]+)", re.I)),
    ("need",      re.compile(r"\b(i\s+need|i\s+could\s+use)\s+(?P<x>[^.?!]+)", re.I)),
    ("preference",re.compile(r"\b(i\s+(really\s+)?like|i\s+love)\s+(?P<x>[^.?!]+)", re.I)),
]

def _normalize(txt: str) -> str:
    return " ".join(txt.strip().split())

def _as_fact(sentence: str) -> Dict[str, Any]:
    return {"role": "system", "type": "fact", "text": _normalize(sentence), "ts": _now()}

# ---------- Reflector ----------

class Reflector:
    def __init__(self, reflect_every: int = 12, max_ctx: int = 220) -> None:
        """
        reflect_every: run only if >= this many new utterances since last reflect
        max_ctx      : scan at most this many recent utterances (newest-first)
        """
        self.reflect_every = reflect_every
        self.max_ctx = max_ctx

    def maybe_reflect(self) -> Dict[str, Any]:
        """
        Attempt one reflection pass if enough new utterances arrived.
        Never raises; returns a result dict with keys:
            reflected (bool), reason (str), n_facts (int), n_summaries (int)
        """
        meta = _load_meta()
        last_idx = int(meta.get("last_reflected_idx", -1))

        data = _read_all(STORE)
        if not data:
            return {"reflected": False, "reason": "no data", "n_facts": 0, "n_summaries": 0}

        # Only consider new utterances since last pass
        new_items = [r for r in data if r.get("_idx", -1) > last_idx]
        # If not enough, skip to save cycles
        if len(new_items) < self.reflect_every:
            return {
                "reflected": False,
                "reason": f"only {len(new_items)}/{self.reflect_every} new items",
                "n_facts": 0,
                "n_summaries": 0,
            }

        # Limit context size (newest first for scanning)
        ctx = (data[-self.max_ctx:]) if len(data) > self.max_ctx else data
        n_facts = self._extract_and_write_facts(ctx)
        n_summaries = self._write_summary(ctx)

        # Update watermark (highest seen index)
        max_idx = max((r.get("_idx", -1) for r in data), default=last_idx)
        meta["last_reflected_idx"] = max_idx
        _save_meta(meta)

        return {
            "reflected": True,
            "reason": "ok",
            "n_facts": n_facts,
            "n_summaries": n_summaries,
        }

    # ----- internals -----

    def _extract_and_write_facts(self, ctx: List[Dict[str, Any]]) -> int:
        """
        Extract fact-like statements from the newest ~max_ctx messages.
        Deduplicate against existing facts by case-insensitive text.
        """
        # Build a set of existing fact texts to avoid duplicates
        existing_facts = set()
        for r in ctx:
            if r.get("type") == "fact":
                t = _normalize(r.get("text", "")).lower()
                if t:
                    existing_facts.add(t)

        new_facts: List[str] = []

        # Scan only utterances
        for r in reversed(ctx):  # oldest -> newest for stable phrasing
            role = r.get("role")
            text = str(r.get("text") or "").strip()
            if role not in {"user", "assistant"} or not text:
                continue

            # Regex-based slots
            for _, pat in _PATTERNS:
                for m in pat.finditer(text):
                    x = _normalize(m.group("x"))
                    if not x:
                        continue
                    # canonicalize to a short factual sentence
                    sent = None
                    if "like" in m.group(0).lower() or "love" in m.group(0).lower():
                        sent = f"Likes {x}."
                    elif "need" in m.group(0).lower() or "could use" in m.group(0).lower():
                        sent = f"Needs {x}."
                    elif "live in" in m.group(0).lower() or " am in " in m.group(0).lower() or "’m in" in m.group(0).lower():
                        sent = f"Location mentioned: {x}."
                    elif "i am" in m.group(0).lower() or "i'm" in m.group(0).lower():
                        sent = f"Identity: {x}."
                    if sent:
                        key = sent.lower()
                        if key not in existing_facts:
                            existing_facts.add(key)
                            new_facts.append(sent)

            # Generic short declarative ending with a period (<= 20 words)
            if text.endswith("."):
                words = text.split()
                if 1 <= len(words) <= 20:
                    sent = _normalize(text)
                    key = sent.lower()
                    if key not in existing_facts:
                        existing_facts.add(key)
                        new_facts.append(sent)

        # Write new fact records
        for s in new_facts:
            _append_jsonl(STORE, _as_fact(s))
        return len(new_facts)

    def _write_summary(self, ctx: List[Dict[str, Any]]) -> int:
        """
        Make a tiny rolling summary from the most recent 6 utterances.
        """
        utterances = [r for r in ctx if r.get("role") in {"user", "assistant"}]
        if not utterances:
            return 0
        tail = utterances[-6:]
        parts = []
        for r in tail:
            role = r.get("role", "?")
            txt = str(r.get("text") or "").strip().replace("\n", " ")
            if not txt:
                continue
            if len(txt) > 80:
                txt = txt[:77] + "..."
            parts.append(f"{role}: {txt}")
        if not parts:
            return 0
        summary = " | ".join(parts)
        rec = {"role": "system", "type": "summary", "text": summary, "ts": _now()}
        _append_jsonl(STORE, rec)
        return 1

# ---------- Convenience function ----------

# Default instance mirrors your memory_api shim expectations
_default_reflector = Reflector(reflect_every=16, max_ctx=220)

def maybe_reflect() -> Dict[str, Any]:
    """
    Run one safe reflection attempt with default params.
    Never raises; returns a result dict.
    """
    try:
        return _default_reflector.maybe_reflect()
    except Exception as e:
        return {"reflected": False, "error": str(e)}