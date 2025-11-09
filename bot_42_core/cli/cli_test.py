#!/usr/bin/env python3
"""
Lightweight CLI for Bot 42.

Usage examples:
  python3 cli_test.py say sage "reactor main into modules"
  python3 cli_test.py run
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

# --- Make sure project root is importable (works outside Replit too) ---
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- Imports from your package ---
from bot_42_core.cli.commands import say_as, run_default_itinerary


def cmd_say(args: argparse.Namespace) -> int:
    text = " ".join(args.text) if isinstance(args.text, list) else args.text
    print(say_as(args.persona, text))
    return 0


def cmd_run(_: argparse.Namespace) -> int:
    count = run_default_itinerary()
    print(f"Ran tasks: {count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="42", description="Bot 42 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    say = sub.add_parser("say", help="Speak with a given personality")
    say.add_argument("persona", help="persona key (e.g., sage, hype, scout)")
    say.add_argument("text", nargs=argparse.REMAINDER, help="text to send")
    say.set_defaults(func=cmd_say)

    run = sub.add_parser("run", help="Run the default itinerary once")
    run.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())