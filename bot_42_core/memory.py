# memory.py
# 42 :: Lightweight JSONL memory store (append-only, safe, local)

from __future__ import annotations
from typing import Dict, Any, Iterable, List, Optional
from datetime import datetime
import os, json, io

DEFAULT_FILENAME = "memory_store.jsonl"
MAX_LINES = 5000  # soft cap to prevent runaway file size

class MemoryStore:
    def __init__(self, base_dir: str, filename: str = DEFAULT_FILENAME):
        self.path = os.path.join(base_dir, filename)
        os.makedirs(base_dir, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                pass  # create empty file

    def add(self, record: Dict[str, Any]) -> None:
        """Append a single JSON object (one per line)."""
        rec = dict(record)
        rec.setdefault("time", datetime.utcnow().isoformat() + "Z")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._truncate_tail(MAX_LINES)

    def _truncate_tail(self, max_lines: int) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) <= max_lines:
                return
            keep = lines[-max_lines:]
            with open(self.path, "w", encoding="utf-8") as f:
                f.writelines(keep)
        except Exception:
            # best-effort; never crash the agent on memory maintenance
            pass

    def iter_all(self) -> Iterable[Dict[str, Any]]:
        """Yield all memory records."""
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue

    def last(self, n: int = 10) -> List[Dict[str, Any]]:
        buf: List[Dict[str, Any]] = []
        # simple approach: read all then slice tail
        for rec in self.iter_all():
            buf.append(rec)
        return buf[-max(0, n):]

    def clear(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            pass

    def stats(self) -> Dict[str, Any]:
        count = 0
        first_time: Optional[str] = None
        last_time: Optional[str] = None
        modules: Dict[str, int] = {}
        modes: Dict[str, int] = {}

        for rec in self.iter_all():
            count += 1
            t = rec.get("time")
            if first_time is None:
                first_time = t
            last_time = t or last_time
            # count modules observed in results
            for r in rec.get("results", []):
                m = (r.get("module") or "unknown").lower()
                modules[m] = modules.get(m, 0) + 1
            mode = (rec.get("mode") or "unknown").lower()
            modes[mode] = modes.get(mode, 0) + 1

        return {
            "count": count,
            "first_time": first_time,
            "last_time": last_time,
            "modules": modules,
            "modes": modes,
            "path": self.path,
        }

    def find(self, substring: str, limit: int = 20) -> List[Dict[str, Any]]:
        sub = (substring or "").lower()
        out: List[Dict[str, Any]] = []
        for rec in self.iter_all():
            hay = f"{rec.get('handled','')} {rec.get('original','')} {rec.get('input','')}".lower()
            if sub in hay:
                out.append(rec)
                if len(out) >= limit:
                    break
        return out
