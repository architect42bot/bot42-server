# agent.py (v3) — memory-first, autonomy-aware, direct+auto planner
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import importlib, json, os, re, sys, traceback

__version__ = "agent-v3.0-autonomy"
print(f"[agent {__version__}] loaded from: {__file__}")

# ───────────────────────────────── Memory ─────────────────────────────────
try:
    from memory import MemoryStore
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MEM = MemoryStore(_BASE_DIR)
except Exception as _e:
    MEM = None
    print(f"[agent {__version__}] memory disabled ({_e})")

def _mem_add(obj: Dict[str, Any]) -> None:
    try:
        if MEM:
            MEM.add(obj)
    except Exception:
        pass

# ───────────────────────────────── Config ─────────────────────────────────
@dataclass
class AgentConfig:
    require_approval: bool = False
    dry_run: bool = False
    max_steps: int = 3
    allow_modules: List[str] = None
    def __post_init__(self):
        if self.allow_modules is None:
            # autonomy included so you can call it directly if you want
            self.allow_modules = ["infiltrate", "intervene", "offense", "autonomy"]

CFG = AgentConfig()

# ─────────────────────────────── Patterns ────────────────────────────────
ABSOLUTES  = re.compile(r"\b(ONLY ONE WAY|ALWAYS|NEVER)\b", re.I)
RISK_WORDS = re.compile(r"\b(harm|kill|violence|weapon|illegal)\b", re.I)
EMAIL_RE   = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_RE     = re.compile(r"(https?://[^\s]+)", re.I)

# ─────────────────────────────── Utilities ───────────────────────────────
def _is_tty() -> bool:
    try: return sys.stdin.isatty()
    except Exception: return False

def _maybe_json_text(t: str) -> str:
    t = (t or "").strip()
    if t.startswith("{"):
        try:
            obj = json.loads(t)
            if isinstance(obj, dict) and "text" in obj:
                return str(obj["text"])
        except Exception:
            pass
    return t

def _import_run(modname: str) -> Callable[[str], Any]:
    mod = importlib.import_module(modname)
    fn = getattr(mod, "run", None)
    if not callable(fn):
        raise AttributeError(f"module '{modname}' has no run()")
    return fn

def _safe_exec(modname: str, goal: str) -> Dict[str, Any]:
    """Execute module.run(goal) safely and normalize shape."""
    try:
        fn = _import_run(modname)
    except Exception as e:
        return {"module": modname, "status": "error", "error": f"import_failed: {e}", "result": None,
                "trace": traceback.format_exc(limit=2)}
    try:
        out = fn(goal)
        if not isinstance(out, dict):
            out = {"status": "ok", "module": modname, "result": out}
        out.setdefault("module", modname)
        out.setdefault("status", "ok")
        return out
    except Exception as e:
        return {"module": modname, "status": "error", "error": f"exec_failed: {e}", "result": None,
                "trace": traceback.format_exc(limit=2)}

# ───────────────────────────── Memory Commands ───────────────────────────
def _handle_memory(raw: str) -> Optional[Dict[str, Any]]:
    m = re.match(r"^\s*memory\s*:\s*(.*)$", raw, re.I)
    if not m:
        return None
    rest = (m.group(1) or "").strip()
    if MEM is None:
        return {"status": "error", "module": "agent", "mode": "memory",
                "error": "memory disabled (memory.py not available)"}

    if rest.lower().startswith("stats"):
        return {"status": "ok", "module": "agent", "mode": "memory", "handled": "memory: stats",
                "report": {"arsenal": "42::Memory", "stats": MEM.stats()}}

    if rest.lower().startswith("last"):
        n = 10
        mm = re.search(r"last\s+(\d+)", rest, re.I)
        if mm: n = max(1, min(100, int(mm.group(1))))
        return {"status": "ok", "module": "agent", "mode": "memory", "handled": f"memory: last {n}",
                "report": {"arsenal": "42::Memory", "last": MEM.last(n)}}

    if rest.lower().startswith("clear"):
        MEM.clear()
        return {"status": "ok", "module": "agent", "mode": "memory", "handled": "memory: clear",
                "report": {"arsenal": "42::Memory", "cleared": True, "path": MEM.path}}

    if rest.lower().startswith("find"):
        q = rest[4:].strip()
        if not q:
            return {"status": "error", "module": "agent", "mode": "memory", "error": "empty query"}
        rows = MEM.find(q, limit=20)
        return {"status": "ok", "module": "agent", "mode": "memory", "handled": f"memory: find {q}",
                "report": {"arsenal": "42::Memory", "query": q, "matches": rows}}

    return {"status": "error", "module": "agent", "mode": "memory",
            "error": f"unknown memory command: {rest}"}

# ────────────────────────────── Routing ──────────────────────────────────
def _route_direct(raw: str) -> Optional[Dict[str, Any]]:
    """Match 'offense|infiltrate|intervene:' and pass header to module parsers."""
    m = re.match(r"^\s*(offense|infiltrate|intervene)\s*:(.*)$", raw, re.I)
    if not m: return None
    target = m.group(1).lower()
    return {"mode": "direct", "steps": [target], "payload": raw}

def _route_autonomy(raw: str) -> Optional[str]:
    """Return the tag if it starts with auto/plan/chain, else None."""
    low = (raw or "").lower().strip()
    for tag in ("auto:", "autonomy:", "plan:", "chain:"):
        if low.startswith(tag):
            return tag
    return None

# ────────────────────────────── Planner ──────────────────────────────────
def _autonomy_plan(raw: str) -> Dict[str, Any]:
    """Fallback planner if user just types free text (no explicit routing)."""
    goal = _maybe_json_text(raw)
    steps: List[str] = ["infiltrate"]
    if any(p.search(goal) for p in (ABSOLUTES, RISK_WORDS, EMAIL_RE, URL_RE)):
        steps.append("intervene")
    steps.append("offense")
    steps = [s for s in steps if s in CFG.allow_modules][: CFG.max_steps]
    return {"mode": "auto", "original": goal, "steps": steps}

def _maybe_approve(plan: Dict[str, Any]) -> bool:
    if not CFG.require_approval: return True
    if not _is_tty(): return True
    print(f"[agent {__version__}] plan:", " → ".join(plan.get("steps", [])))
    try:
        return input("[agent] approve plan? (y/n) ").strip().lower() in {"y","yes"}
    except Exception:
        return True

# ───────────────────────────── Public API ────────────────────────────────
def run(text: str = "") -> Dict[str, Any]:
    """
    Entry point used by chat.py.
    - memory: commands short-circuit here
    - auto/plan/chain: routed to autonomy.run(...)
    - direct: routed to module.run(...)
    - otherwise: minimal autonomy (scout -> maybe intervene -> offense)
    """
    started = datetime.utcnow().isoformat() + "Z"
    raw = text or ""

    # 1) Memory
    mem = _handle_memory(raw)
    if mem is not None:
        _mem_add({"time": started, "mode": "memory", "input": raw, "results": [mem]})
        return mem

    # 2) Explicit autonomy (auto/plan/chain)
    tag = _route_autonomy(raw)
    if tag:
        try:
            from autonomy import run as auto_run
        except Exception as e:
            return {"status": "error", "module": "agent",
                    "error": f"autonomy unavailable: {e}"}
        out = auto_run(raw)  # autonomy handles its own structure/prints
        _mem_add({"time": started, "mode": "autonomy", "input": raw, "steps": ["autonomy"], "results": [out]})
        return out

    # 3) Direct routing (offense/infiltrate/intervene)
    direct = _route_direct(raw)
    if direct:
        if CFG.dry_run:
            _mem_add({"time": started, "mode": "direct", "input": raw, "steps": direct["steps"], "results": []})
            return {"status": "ok", "module": "agent", "mode": "direct",
                    "config": asdict(CFG), "steps": direct["steps"],
                    "results": [], "note": "dry_run"}
        results = [_safe_exec(step, direct["payload"]) for step in direct["steps"]]
        _mem_add({"time": started, "mode": "direct", "input": raw, "steps": direct["steps"], "results": results})
        return {"status": "ok", "module": "agent", "mode": "direct",
                "config": asdict(CFG), "steps": direct["steps"], "results": results}

    # 4) Minimal autonomy (free text)
    plan = _autonomy_plan(raw)
    if not _maybe_approve(plan):
        _mem_add({"time": started, "mode": "auto", "input": raw, "steps": plan["steps"], "results": [], "note": "rejected"})
        return {"status": "ok", "module": "agent", "mode": "auto",
                "config": asdict(CFG), "steps": plan["steps"], "results": [],
                "note": "plan rejected"}

    if CFG.dry_run:
        _mem_add({"time": started, "mode": "auto", "input": raw, "steps": plan["steps"], "results": [], "note": "dry_run"})
        return {"status": "ok", "module": "agent", "mode": "auto",
                "config": asdict(CFG), "steps": plan["steps"], "results": [],
                "note": "dry_run"}

    # execute chain
    results: List[Dict[str, Any]] = []
    payload = plan["original"]
    for step in plan["steps"]:
        res = _safe_exec(step, payload)
        results.append(res)
        # let intervene rewrite payload for offense
        if step == "intervene" and res.get("status") == "ok":
            try:
                rewritten = res.get("report", {}).get("result", {}).get("full")
                if isinstance(rewritten, str) and rewritten:
                    payload = rewritten
            except Exception:
                pass

    _mem_add({"time": started, "mode": "auto", "input": raw, "steps": plan["steps"], "results": results})
    return {"status": "ok", "module": "agent", "mode": "auto",
            "config": asdict(CFG), "steps": plan["steps"], "results": results}

# Optional alias some launchers expect
def process_with_agents(text: str = "") -> Dict[str, Any]:
    return run(text)