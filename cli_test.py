# cli_test.py
from infiltration import infiltrate

BANNER = """
┌──────────────────────────────────────────────┐
│                BOT 42 — CONSOLE              │
└──────────────────────────────────────────────┘
"""

def main():
    print(BANNER)
    while True:
        try:
            msg = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return
        if msg in {"exit","quit",":q"}:
            print("bye.")
            return
        if msg.startswith("infiltrate"):
            parts = msg.split()
            target = parts[1] if len(parts) > 1 else "the machine"
            depth = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 3
            report = infiltrate(target, depth)
            print("Final:", report["status"])
            continue
        print("(try: infiltrate [target] [depth] or exit)")

if __name__ == "__main__":
    main()