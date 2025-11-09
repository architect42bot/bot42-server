# features/law_systems/cli.py
from __future__ import annotations

import argparse
import json
from typing import List
from .storage import LAWDB

from importlib import import_module
from typing import Callable, Dict, List

# Registered command groups (name -> handler(argv) -> int)
groups: Dict[str, Callable[[List[str]], int]] = {}

def _load_optional(*candidates: str):
    """Try several module paths; return the first that imports, else None."""
    for path in candidates:
        try:
            return import_module(path)
        except Exception:
            continue
    return None

# --- Law system group (optional) ---
# Your law CLI lives at: bot_42_core/features/law_systems/cli.py
law_mod = _load_optional(
    "bot_42_core.features.law_systems.cli",  # canonical
    "features.law_systems.cli",              # legacy fallback
)
if law_mod and hasattr(law_mod, "main"):
    # expects cli.py to expose: def main(argv: List[str]) -> int
    groups["law"] = lambda argv: law_mod.main(argv)

# -----------------------------
# Helpers
# -----------------------------
def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _ok(ok: bool) -> str:
    return "✅ Success" if ok else "⚠️ Not found"


def _auto_save():
    """Persist DB to disk after any write operation."""
    try:
        LAWDB.save_json()
    except Exception as e:
        print(f"[warn] could not save DB: {e}")


# -----------------------------
# Command Implementations
# -----------------------------
def cmd_add_citizen(args):
    ok = LAWDB.add_citizen(args.name)
    _auto_save()
    _print_json({"added": ok, "citizen": args.name}) if args.json else print(
        "✅ Citizen added." if ok else "ℹ️  Already exists."
    )


def cmd_report(args):
    cid = LAWDB.report_conflict(
        args.desc, parties=args.party, kind=args.kind, severity=args.severity
    )
    _auto_save()
    data = {
        "id": cid,
        "status": "open",
        "kind": args.kind,
        "severity": args.severity,
        "parties": args.party or [],
        "description": args.desc,
    }
    _print_json(data) if args.json else print(f"✅ Conflict #{cid} reported.")


def cmd_list_conflicts(args):
    conflicts = LAWDB.conflicts
    if args.json:
        _print_json(conflicts)
        return
    if not conflicts:
        print("No conflicts.")
        return
    for c in conflicts:
        cid = c.get("id", "?")
        print(
            f"• #{cid} [{c.get('status','?')}/{c.get('severity','?')}] {c.get('description','')}"
        )


def cmd_set_status(args):
    ok = LAWDB.set_status(args.id, args.status)
    _auto_save()
    _print_json({"updated": ok, "id": args.id, "status": args.status}) if args.json else print(
        _ok(ok)
    )


def cmd_set_severity(args):
    ok = LAWDB.set_severity(args.id, args.severity)
    _auto_save()
    _print_json({"updated": ok, "id": args.id, "severity": args.severity}) if args.json else print(
        _ok(ok)
    )


def cmd_assign(args):
    ok = LAWDB.assign_conflict(args.id, args.mediator)
    _auto_save()
    _print_json({"assigned": ok, "id": args.id, "to": args.mediator}) if args.json else print(
        _ok(ok)
    )


def cmd_tag(args):
    ok = LAWDB.add_tag(args.id, args.tag)
    _auto_save()
    _print_json({"tagged": ok, "id": args.id, "tag": args.tag}) if args.json else print(_ok(ok))


def cmd_evidence(args):
    if args.subcmd == "add":
        ok = LAWDB.add_evidence(args.id, args.item)
        _auto_save()
        _print_json({"added": ok, "id": args.id}) if args.json else print(_ok(ok))
    else:
        c = LAWDB.get_conflict_by_id(args.id)
        if args.json:
            _print_json({"id": args.id, "evidence": c.get("evidence", []) if c else None})
        else:
            if not c:
                print("⚠️ Not found")
                return
            print(f"📂 Evidence for #{args.id}:")
            for i, item in enumerate(c.get("evidence", []), 1):
                print(f"  {i}. {item}")


def cmd_find(args):
    results = LAWDB.find_conflicts(
        keyword=args.kw or "",
        status=args.status,
        tag=args.tag,
        party=args.party,
        kind=args.kind,
    )
    if args.json:
        _print_json({"count": len(results), "results": results})
    else:
        print(f"🔎 {len(results)} result(s):")
        for c in results:
            print(
                f"  • #{c.get('id','?')} [{c.get('status','?')}/{c.get('severity','?')}] {c.get('description','')}"
            )


def cmd_records(args):
    records = LAWDB.get_records(args.name)
    if args.only == "resolved":
        records = [r for r in records if r.get("status") == "resolved"]
    elif args.only == "open":
        records = [r for r in records if r.get("status") != "resolved"]
    if args.json:
        _print_json({"citizen": args.name, "records": records})
    else:
        print(f"📒 Records for {args.name}:")
        for r in records:
            print(f"  • #{r.get('id','?')} [{r.get('status','?')}] {r.get('description','')}")


def cmd_delete_conflict(args):
    ok = LAWDB.delete_conflict(args.id)
    _auto_save()
    _print_json({"deleted": ok, "id": args.id}) if args.json else print(_ok(ok))


def cmd_export_db(args):
    path = LAWDB.save_json(args.path)
    _print_json({"exported_to": path}) if args.json else print(f"✅ Exported DB to {path}")


def cmd_stats(args):
    stats = LAWDB.stats()
    _print_json(stats) if args.json else print(
        f"Citizens: {stats.get('citizens',0)} | "
        f"Conflicts: {stats.get('conflicts_total',0)} "
        f"(open {stats.get('conflicts_open',0)}, resolved {stats.get('conflicts_resolved',0)})"
    )


# -----------------------------
# Parser Builder
# -----------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="42 law", add_help=True)
    # root-level --json so it can appear before OR after the subcommand
    p.add_argument("--json", action="store_true", help="print JSON output")
    sub = p.add_subparsers(dest="cmd", metavar="law_command", required=True)

    def add_json(sp):
        sp.add_argument("--json", action="store_true", help="print JSON output")

    s = sub.add_parser("add-citizen", help="add a citizen")
    s.add_argument("name")
    add_json(s)
    s.set_defaults(func=cmd_add_citizen)

    s = sub.add_parser("report", help="report a conflict")
    s.add_argument("desc", help="quoted description")
    s.add_argument("--party", action="append", help="party involved (repeatable)")
    s.add_argument("--kind", default="physical")
    s.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"])
    add_json(s)
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("list-conflicts", help="list all conflicts")
    add_json(s)
    s.set_defaults(func=cmd_list_conflicts)

    s = sub.add_parser("set-status", help="set conflict status")
    s.add_argument("id", type=int)
    s.add_argument("status", choices=["open", "resolved", "dismissed"])
    add_json(s)
    s.set_defaults(func=cmd_set_status)

    s = sub.add_parser("set-severity", help="set conflict severity")
    s.add_argument("id", type=int)
    s.add_argument("severity", choices=["low", "medium", "high", "critical"])
    add_json(s)
    s.set_defaults(func=cmd_set_severity)

    s = sub.add_parser("assign", help="assign a mediator")
    s.add_argument("id", type=int)
    s.add_argument("mediator")
    add_json(s)
    s.set_defaults(func=cmd_assign)

    s = sub.add_parser("tag", help="tag a conflict")
    s.add_argument("id", type=int)
    s.add_argument("tag")
    add_json(s)
    s.set_defaults(func=cmd_tag)

    s = sub.add_parser("evidence", help="manage evidence")
    s_sub = s.add_subparsers(dest="subcmd", required=True)
    s1 = s_sub.add_parser("add", help="add evidence")
    s1.add_argument("id", type=int)
    s1.add_argument("item")
    add_json(s1)
    s1.set_defaults(func=cmd_evidence)
    s2 = s_sub.add_parser("list", help="list evidence")
    s2.add_argument("id", type=int)
    add_json(s2)
    s2.set_defaults(func=cmd_evidence)

    s = sub.add_parser("find", help="search conflicts")
    s.add_argument("--kw")
    s.add_argument("--status", choices=["open", "resolved", "dismissed"])
    s.add_argument("--tag")
    s.add_argument("--party")
    s.add_argument("--kind")
    add_json(s)
    s.set_defaults(func=cmd_find)

    s = sub.add_parser("records", help="show records for a citizen")
    s.add_argument("name")
    s.add_argument("--only", choices=["open", "resolved"])
    add_json(s)
    s.set_defaults(func=cmd_records)

    s = sub.add_parser("delete-conflict", help="delete a conflict by ID")
    s.add_argument("id", type=int)
    add_json(s)
    s.set_defaults(func=cmd_delete_conflict)

    s = sub.add_parser("export-db", help="export database to file")
    s.add_argument("path", nargs="?", default="lawdb.json")
    add_json(s)
    s.set_defaults(func=cmd_export_db)

    s = sub.add_parser("stats", help="show database stats")
    add_json(s)
    s.set_defaults(func=cmd_stats)

    from .laws import list_laws, remove_law, apply_laws_to_conflict

    # subparser: laws
    s = sub.add_parser("laws", help="inspect and use codified laws")
    s_sub = s.add_subparsers(dest="laws_cmd", required=True)

    s1 = s_sub.add_parser("list", help="list available laws")
    s1.add_argument("--json", action="store_true")
    s1.set_defaults(func=lambda a: _print_json({"laws": list_laws()}) if a.json else
                    [print(f"- {l['key']}: {l['title']} ({l['kind']})") for l in list_laws()])

    s2 = s_sub.add_parser("apply", help="apply laws to a conflict")
    s2.add_argument("id", type=int)
    s2.add_argument("--json", action="store_true")
    def _laws_apply(args):
        out = apply_laws_to_conflict(args.id)
        _auto_save()
        _print_json(out) if args.json else (print(f"Matched: {', '.join(out['matched']) or '(none)'}"),
                                            [print(f"  • {s}") for s in out["suggested"]])
    s2.set_defaults(func=_laws_apply)

    s3 = s_sub.add_parser("remove", help="remove a law by key")
    s3.add_argument("key")
    s3.add_argument("--json", action="store_true")
    s3.set_defaults(func=lambda a: (_print_json({"removed": remove_law(a.key)}) if a.json
                                    else print("✅ Removed" if remove_law(a.key) else "⚠️ Not found")))
    
    return p


# -----------------------------
# Entry Point
# -----------------------------
def main(argv: List[str]) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    func = getattr(ns, "func", None)
    if not callable(func):
        parser.print_help()
        return 2
    func(ns)
    return 0


# Export LAW_COMMANDS for dispatcher (optional dynamic usage)
LAW_COMMANDS = {
    "add-citizen": cmd_add_citizen,
    "report": cmd_report,
    "list-conflicts": cmd_list_conflicts,
    "set-status": cmd_set_status,
    "set-severity": cmd_set_severity,
    "assign": cmd_assign,
    "tag": cmd_tag,
    "evidence": cmd_evidence,
    "find": cmd_find,
    "records": cmd_records,
    "delete-conflict": cmd_delete_conflict,
    "export-db": cmd_export_db,
    "stats": cmd_stats,
}