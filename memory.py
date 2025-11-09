from __future__ import annotations
import json, os, time, uuid
from typing import List, Dict, Any, Optional

def _now() -> float:
    return time.time()

def _tokenize(text: str) -> List[str]:
    out, buf = [], []
    for ch in text.lower():
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                out.append("".join(buf))
                buf = []
    if buf:
        out.append("".join(buf))
    return out

def _uniq(seq):
    seen = set()
    for x in seq:
        if x not in seen:
            seen.add(x)
            yield x

class MemoryStore:
    """
    File-based persistent memory with scoring by overlap + recency + importance.
    """
    def __init__(self, path: str = "memory_store.json", autosave: bool = True):
        self.path = path
        self.autosave = autosave
        self.memories: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.memories = data
            except Exception:
                self.memories = {}
        else:
            self._flush()

    def _flush(self) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def save(self) -> None:
        self._flush()

    def remember(self, text: str, *, tags: Optional[List[str]] = None, importance: float = 0.5,
                 ttl_seconds: Optional[int] = None, meta: Optional[Dict[str, Any]] = None) -> str:
        mid = str(uuid.uuid4())
        now = _now()
        record = {
            "id": mid,
            "text": text.strip(),
            "tokens": list(_uniq(_tokenize(text))),
            "tags": sorted(list(_uniq([t.lower() for t in (tags or [])]))),
            "importance": float(max(0.0, min(1.0, importance))),
            "created_at": now,
            "last_access": now,
            "ttl_seconds": int(ttl_seconds) if ttl_seconds is not None else None,
            "meta": meta or {},
        }
        self.memories[mid] = record
        if self.autosave:
            self._flush()
        return mid

    def update(self, memory_id: str, **fields) -> bool:
        m = self.memories.get(memory_id)
        if not m:
            return False
        for k, v in fields.items():
            if k == "text":
                m["text"] = str(v)
                m["tokens"] = list(_uniq(_tokenize(m["text"])))
            elif k == "tags" and isinstance(v, list):
                m["tags"] = sorted(list(_uniq([t.lower() for t in v])))
            else:
                m[k] = v
        if self.autosave:
            self._flush()
        return True

    def forget(self, memory_id: str) -> bool:
        if memory_id in self.memories:
            del self.memories[memory_id]
            if self.autosave:
                self._flush()
            return True
        return False

    def forget_where(self, *, tag: Optional[str] = None, contains: Optional[str] = None) -> int:
        to_del = []
        tag = tag.lower() if tag else None
        needle = contains.lower() if contains else None
        for mid, m in self.memories.items():
            if tag and tag not in m.get("tags", []):
                continue
            if needle and needle not in m.get("text", "").lower():
                continue
            to_del.append(mid)
        for mid in to_del:
            del self.memories[mid]
        if to_del and self.autosave:
            self._flush()
        return len(to_del)

    def _expired(self, m: Dict[str, Any], now: float) -> bool:
        ttl = m.get("ttl_seconds")
        if ttl is None:
            return False
        return (now - float(m.get("created_at", now))) > ttl

    def _score(self, query_tokens: List[str], m: Dict[str, Any], now: float) -> float:
        mtoks = m["tokens"]
        if not mtoks:
            overlap = 0.0
        else:
            inter = len(set(query_tokens) & set(mtoks))
            union = len(set(query_tokens) | set(mtoks))
            overlap = inter / max(1, union)
        age_secs = max(1.0, now - float(m.get("last_access", now)))
        half_life = 10 * 24 * 3600
        recency = 0.5 ** (age_secs / half_life)
        importance = float(m.get("importance", 0.5))
        return (0.55 * overlap) + (0.25 * recency) + (0.20 * importance)

    def recall(self, query: str, *, k: int = 5, any_tag: Optional[List[str]] = None,
               must_tags: Optional[List[str]] = None, include_expired: bool = False,
               update_access_time: bool = True) -> List[Dict[str, Any]]:
        now = _now()
        qtokens = list(_uniq(_tokenize(query)))
        any_tag = [t.lower() for t in (any_tag or [])]
        must_tags = [t.lower() for t in (must_tags or [])]
        candidates = []
        for m in self.memories.values():
            if not include_expired and self._expired(m, now):
                continue
            mtags = m.get("tags", [])
            if must_tags and not all(t in mtags for t in must_tags):
                continue
            if any_tag and not any(t in mtags for t in any_tag):
                continue
            score = self._score(qtokens, m, now)
            candidates.append((score, m))
        candidates.sort(key=lambda x: x[0], reverse=True)
        out = [m for _, m in candidates[:k]]
        if update_access_time:
            changed = False
            ts = _now()
            for m in out:
                if m.get("last_access") != ts:
                    m["last_access"] = ts
                    changed = True
            if changed and self.autosave:
                self._flush()
        return out

    def prune_expired(self) -> int:
        now = _now()
        to_del = [mid for mid, m in self.memories.items() if self._expired(m, now)]
        for mid in to_del:
            del self.memories[mid]
        if to_del and self.autosave:
            self._flush()
        return len(to_del)

    def stats(self) -> Dict[str, Any]:
        now = _now()
        total = len(self.memories)
        expired = sum(1 for m in self.memories.values() if self._expired(m, now))
        return {"total": total, "expired": expired, "active": total - expired}
