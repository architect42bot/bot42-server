# features/storage.py
from __future__ import annotations

import json
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, MutableMapping, Optional, Tuple

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_STORAGE_DIR = BASE_DIR / "storage"
DEFAULT_PATH = DEFAULT_STORAGE_DIR / "state.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, data: Any) -> None:
    """
    Safely write JSON to disk using a temp file + atomic replace.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp_path).replace(path)  # atomic on POSIX
    finally:
        # If something went wrong before replace, ensure temp file is gone
        try:
            tmp = Path(tmp_path)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
        except Exception:
            pass


class Storage:
    """
    Minimal, durable JSON-backed key/value store for 42.

    - Atomic writes to prevent corruption on crash
    - Thread-safe (basic RLock)
    - Automatic directory creation
    - Corruption-safe: backs up unreadable JSON and resets to {}
    - Context manager `batch()` to group many writes into one save
    - Optional namespacing via `sub(namespace)`
    """

    def __init__(self, path: Optional[str | Path] = None, autosave: bool = True) -> None:
        self.path: Path = Path(path) if path else DEFAULT_PATH
        self.autosave = autosave
        self._lock = threading.RLock()
        self.data: Dict[str, Any] = {}
        self._load()

    # ---------- Core I/O ----------
    def _load(self) -> None:
        with self._lock:
            try:
                if self.path.exists():
                    with self.path.open("r", encoding="utf-8") as f:
                        obj = json.load(f)
                        if isinstance(obj, dict):
                            self.data = obj
                        else:
                            # Non-dict root; reset to {}
                            self._backup_corrupt(reason="non-dict root")
                            self.data = {}
                else:
                    # Ensure directory exists for first save
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self.data = {}
            except Exception as e:
                # Backup unreadable file and start fresh
                self._backup_corrupt(reason=f"json read error: {e!r}")
                self.data = {}

    def _backup_corrupt(self, reason: str) -> None:
        try:
            stamp = _utc_now_iso().replace(":", "-")
            backup = self.path.with_suffix(self.path.suffix + f".corrupt-{stamp}.bak")
            # Best-effort raw copy
            if self.path.exists():
                backup.write_bytes(self.path.read_bytes())
            # Also log a small note next to it
            note = backup.with_suffix(backup.suffix + ".txt")
            note.write_text(f"Reason: {reason}\nOriginal: {self.path}\n", encoding="utf-8")
        except Exception:
            # Never throw from backup
            pass

    def save(self) -> bool:
        """
        Persist the current data to disk. Returns True on success.
        """
        with self._lock:
            try:
                _atomic_write_json(self.path, self.data)
                return True
            except Exception as e:
                print(f"[storage] save failed: {e}")
                return False

    # ---------- KV API ----------
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self.data[key] = value
            if self.autosave:
                self.save()

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self.data:
                del self.data[key]
                if self.autosave:
                    self.save()

    def update(self, mapping: Mapping[str, Any]) -> None:
        with self._lock:
            self.data.update(mapping)
            if self.autosave:
                self.save()

    def keys(self) -> Iterable[str]:
        with self._lock:
            return list(self.data.keys())

    def values(self) -> Iterable[Any]:
        with self._lock:
            return list(self.data.values())

    def items(self) -> Iterable[Tuple[str, Any]]:
        with self._lock:
            return list(self.data.items())

    def clear(self) -> None:
        with self._lock:
            self.data.clear()
            if self.autosave:
                self.save()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            # Return a shallow copy to avoid external mutation
            return dict(self.data)

    # ---------- Namespacing ----------
    def sub(self, namespace: str) -> "Namespace":
        """
        Return a namespaced view that stores under data[namespace] (a nested dict).
        """
        return Namespace(self, namespace)

    # ---------- Batch writes ----------
    @contextmanager
    def batch(self) -> Iterator["Storage"]:
        """
        Temporarily disable autosave to group multiple changes into one write.
        Usage:
            with storage.batch():
                storage.set("a", 1)
                storage.set("b", 2)
        """
        with self._lock:
            prev = self.autosave
            self.autosave = False
        try:
            yield self
        finally:
            with self._lock:
                self.autosave = prev
                if prev:
                    self.save()


class Namespace:
    """
    A simple view to operate inside storage.data[namespace] (dict).
    """

    def __init__(self, parent: Storage, namespace: str) -> None:
        self.parent = parent
        self.namespace = namespace
        # Ensure backing dict exists
        with self.parent._lock:
            ns = self.parent.data.get(namespace)
            if not isinstance(ns, dict):
                self.parent.data[namespace] = {}

    def _ns(self) -> MutableMapping[str, Any]:
        return self.parent.data[self.namespace]  # type: ignore[return-value]

    def get(self, key: str, default: Any = None) -> Any:
        with self.parent._lock:
            return self._ns().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self.parent._lock:
            self._ns()[key] = value
            if self.parent.autosave:
                self.parent.save()

    def delete(self, key: str) -> None:
        with self.parent._lock:
            if key in self._ns():
                del self._ns()[key]
                if self.parent.autosave:
                    self.parent.save()

    def keys(self) -> Iterable[str]:
        with self.parent._lock:
            return list(self._ns().keys())

    def items(self) -> Iterable[Tuple[str, Any]]:
        with self.parent._lock:
            return list(self._ns().items())

    def clear(self) -> None:
        with self.parent._lock:
            self._ns().clear()
            if self.parent.autosave:
                self.parent.save()