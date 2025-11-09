# bot_42_core/autonomy.py
# Simplified single-file version of autonomy for 42

from __future__ import annotations
import logging
from typing import Any, Optional

log = logging.getLogger("bot42.autonomy")

try:
    from bot_42_core.memory import MemoryStore
except Exception as e:
    MemoryStore = None
    log.warning("MemoryStore unavailable: %s", e)


class Autonomy:
    """Simple autonomy handler with optional persistent memory."""

    def __init__(self, path: str = "memory_store.json", autosave: bool = True):
        if MemoryStore is not None:
            try:
                self.memory = MemoryStore(path=path, autosave=autosave)
                log.info("MemoryStore initialized at %s", path)
            except Exception as e:
                log.error("Failed to init MemoryStore: %s", e)
                self.memory = None
        else:
            self.memory = None
            log.info("Running without MemoryStore")

    def handle(self, text: str) -> dict[str, Any]:
        """Basic handler — expand this later with actual logic."""
        return {"ok": True, "input": text}


# global instance
_autonomy: Optional[Autonomy] = None


def run(text: str = "", **kwargs: Any) -> dict[str, Any]:
    """Public function called by main.py."""
    global _autonomy
    if not text and "payload" in kwargs:
        text = str(kwargs["payload"])
    if _autonomy is None:
        _autonomy = Autonomy()
    try:
        return _autonomy.handle(text)
    except Exception as e:
        log.exception("Autonomy.run failed: %s", e)
        return {"ok": False, "error": str(e), "input": text}