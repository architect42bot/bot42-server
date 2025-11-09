"""
Bridge for 42: initialize_42_core()

Creates a small AI42Core container and attaches subsystems if present:
- Personality  (bot_42_core/features/personality.py)
- Dispatcher   (bot_42_core/features/dispatcher.py  or project-root dispatcher.py)
- Storage      (bot_42_core/features/storage.py)
- Law system   (bot_42_core/features/law_systems.py)

All imports are optional: if a module/class isn't found, it's skipped with a log note.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Optional

__all__ = ["initialize_42_core", "AI42Core"]


# -------------------------------
# Logging
# -------------------------------
def _get_logger() -> logging.Logger:
    log = logging.getLogger("bridge")
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        log.addHandler(h)
    log.setLevel(logging.INFO)
    return log


# -------------------------------
# Core container
# -------------------------------
class AI42Core:
    """Tiny container for 42 subsystems with an optional CLI runner."""
    personality: Any = None
    dispatcher: Any = None
    storage: Any = None
    law_system: Any = None
    cli_main: Optional[Callable[[], None]] = None

    def run(self) -> None:
        """Default run hook: start CLI if present, otherwise just report readiness."""
        log = _get_logger()
        log.info("AI42Core.run() — core initialized.")
        if callable(self.cli_main):
            log.info("Starting CLI via cli_main()…")
            self.cli_main()
        else:
            log.info("No CLI entrypoint found. Nothing to run.")


# -------------------------------
# Helpers
# -------------------------------
def _attach(core: AI42Core, *, attr: str, candidates: list[tuple[str, Optional[str]]]) -> None:
    """
    Try multiple import paths until one succeeds.
    candidates: list of (module_path, class_name_or_None). If class_name is None,
    the module object itself is attached.
    """
    log = _get_logger()
    for mod_path, class_name in candidates:
        try:
            mod = __import__(mod_path, fromlist=["*"])
            obj = getattr(mod, class_name)() if class_name else mod
            setattr(core, attr, obj)
            log.info("✔ attached %-10s from %s%s",
                     attr, mod_path, f".{class_name}" if class_name else "")
            return
        except Exception:
            continue
    log.info("⚠ %-10s not found (skipped)", attr)


# -------------------------------
# Public API
# -------------------------------
def initialize_42_core() -> AI42Core:
    """
    Build an AI42Core and attach whatever subsystems exist.
    Uses relative imports inside the function so missing pieces never crash startup.
    """
    core = AI42Core()

    # Personality
    _attach(core, attr="personality", candidates=[
        ("bot_42_core.features.personality", "Personality"),
        ("bot_42_core.features.personality", None),
    ])

    # Storage
    _attach(core, attr="storage", candidates=[
        ("bot_42_core.features.storage", "Storage"),
        ("bot_42_core.features.storage", None),
    ])

    # Law system (NOTE: imports from features.law_systems — NOT new_law_system)
    _attach(core, attr="law_system", candidates=[
        ("bot_42_core.features.law_systems", "LawSystem"),
        ("bot_42_core.features.law_systems", None),
    ])

    # Dispatcher (features first, then project root as fallback)
    _attach(core, attr="dispatcher", candidates=[
        ("bot_42_core.features.dispatcher", "Dispatcher"),
        ("bot_42_core.features.dispatcher", None),
        ("dispatcher", "Dispatcher"),
        ("dispatcher", None),
    ])

    # Optional CLI entrypoint
    try:
        from bot_42_core.features.cli import main as _cli_main  # type: ignore
        core.cli_main = _cli_main
        _get_logger().info("✔ CLI attached from bot_42_core.features.cli.main")
    except Exception:
        try:
            import cli as _cli_mod  # project root
            core.cli_main = getattr(_cli_mod, "main", getattr(_cli_mod, "run", None))
            if core.cli_main:
                _get_logger().info("✔ CLI attached from project-root cli.py")
        except Exception:
            pass

    _get_logger().info(
        "Core systems attached: personality=%s, dispatcher=%s, storage=%s, law_system=%s",
        bool(core.personality), bool(core.dispatcher), bool(core.storage), bool(core.law_system),
    )
    return core