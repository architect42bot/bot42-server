# bot_42_core/cli/dispatcher.py
from __future__ import annotations

import importlib
import sys
from importlib import import_module

from typing import Dict, Optional, Any, Callable


# Type for a feature module with a main(argv) entrypoint
FeatureModule = Any  # we duck-type: module should expose main(argv: list[str]) -> int


def _load_optional(module_path: str) -> Optional[FeatureModule]:
    """
    Try to import a module; return None if it's missing or import fails.
    We keep errors quiet so the dispatcher can still run with partial features.
    """
    try:
        return importlib.import_module(module_path)
    except Exception:
        return None


def _available_groups(groups: Dict[str, FeatureModule]) -> str:
    if not groups:
        return "(none)"
    return ", ".join(sorted(groups.keys()))


def _print_root_help(groups: Dict[str, FeatureModule]) -> None:
    print("42 CLI")
    print("usage: 42 <group> [args]")
    print()
    print("groups available:", _available_groups(groups))
    print()
    print("examples:")
    print("  42 law add-citizen Alice")
    print('  42 law report "Bob pushed Charlie" --party=Bob --party=Charlie --kind=physical --severity=high')
    print("  42 law list-conflicts --json")


def build_command_groups() -> Dict[str, FeatureModule]:
    """
    Register top-level command groups here.
    Each group should be a module exposing a `main(argv)` function.
    """
    groups: Dict[str, FeatureModule] = {}

    # --- Law System ---
    law_mod = _load_optional("features.law_systems.cli")
    if law_mod and hasattr(law_mod, "main") and callable(law_mod.main):
        groups["law"] = law_mod

    # (Add more feature groups below, following the same pattern)
    # e.g.
    # chat_mod = _load_optional("features.chat.cli")
    # if chat_mod and hasattr(chat_mod, "main") and callable(chat_mod.main):
    #     groups["chat"] = chat_mod

    return groups


def dispatch(argv: list[str]) -> int:
    """
    Entry used by `main.py`:
      from bot_42_core.cli.dispatcher import main as cli_main
      raise SystemExit(cli_main(sys.argv[1:]))

    We expect argv like: ["law", "report", "..."].
    """
    groups = build_command_groups()

    if not argv:
        _print_root_help(groups)
        return 0

    group = argv[0]
    rest = argv[1:]

    mod = groups.get(group)
    if mod is None:
        print(f"error: unknown group '{group}'")
        print("groups available:", _available_groups(groups))
        return 2

    # Delegate to the group's own main(argv)
    try:
        return int(mod.main(rest) or 0)
    except SystemExit as e:
        # If the module uses argparse (which raises SystemExit), normalize the code
        return int(getattr(e, "code", 1) or 0)
    except Exception as e:
        print(f"[dispatcher] {group} crashed: {e}")
        return 1


# Public alias expected by your current main.py
def main(argv: list[str]) -> int:
    return dispatch(argv)