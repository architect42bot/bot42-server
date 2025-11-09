# bot_42_core/autonomy.py
# Minimal, safe autonomy planner for 42 that chains module calls.
# - No background loops.
# - Soft-depends on memory store if present.
# - Works even if only some modules are available.

from __future__ import annotations

import importlib
import time
import re
from typing import Any, Dict, List, Optional, Tuple

# -------------------- optional memory --------------------
try:
    from memory import MemoryStore  # your existing module
except Exception:
    MemoryStore = None  # type: ignore

MEM = MemoryStore(path="memory_store.json", autosave=True) if MemoryStore else None

def _remember(text: str, **kwargs) -> None:
    if MEM:
        try:
            MEM.remember(text, **kwargs)
        except Exception:
            pass

# -------------------- config --------------------
DEFAULT_CFG: Dict[str, Any] = {
    # keep non-interactive by default
    "require_approval": False,
    "dry_run": False,
    "allow_modules": ["offense", "infiltrate", "intervene"],
    "pause_ms": 0,
}

CFG = DEFAULT_CFG  # simple global for now

# -------------------- utils --------------------
def _import_module(mod_name: str):
    """
    Be liberal in imports:
      - try plain 'offense'
      - then 'bot_42_core.offense'
    """
    try:
        return importlib.import_module(mod_name)
    except Exception:
        try:
            return importlib.import_module(f"bot_42_core.{mod_name}")
        except Exception:
            return None

def _run_module(mod, payload: str) -> Any:
    """
    Call module.run with flexible signature:
      run(), run(payload), run(text=...), run(payload=...)
    """
    if mod is None or not hasattr(mod, "run"):
        return {"status": "error", "reason": "module not found or has no run()"}
    fn = getattr(mod, "run")

    try:
        # zero-arg
        if fn.__code__.co_argcount == 0 and not fn.__defaults__:
            return fn()
    except Exception:
        pass

    # try text kw
    try:
        return fn(text=payload)
    except TypeError:
        pass

    # try payload kw
    try:
        return fn(payload=payload)
    except TypeError:
        pass

    # try positional
    try:
        return fn(payload)
    except Exception as e:
        return {"status": "error", "reason": f"exec failed: {e}"}

# -------------------- parse & plan --------------------
# explicit chain pattern: offense.echo -> offense.clarity -> intervene
_CHAIN_STEP = re.compile(r"\s*([a-z_]+)(?:\.([a-z_]+))?\s*$")

def _parse_chain(goal: str) -> Tuple[str, List[Tuple[str, Optional[str], str]]]:
    """
    If the goal contains '->', treat it as an explicit chain.
    Returns (mode, steps) where steps = [(module, subtool, payload), ...]
    For explicit chains we fill the payload with the full goal for simplicity.
    """
    if "->" not in goal:
        return "plan", []
    parts = [p.strip() for p in goal.split("->")]
    steps: List[Tuple[str, Optional[str], str]] = []
    for p in parts:
        m = _CHAIN_STEP.match(p)
        if not m:
            continue
        mod, sub = m.group(1), m.group(2)
        steps.append((mod, sub, goal))
    return "explicit", steps

def _heuristic_plan(goal: str) -> List[Tuple[str, Optional[str], str]]:
    """
    Very small keyword router. Extend as you like.
    Produces a list of (module, subtool, payload)
    """
    g = goal.lower()
    steps: List[Tuple[str, Optional[str], str]] = []

    # clarity / dedupe type requests -> offense tools first
    if any(k in g for k in ("clarity", "clean", "dedupe", "cohere", "echo", "summar")):
        steps.append(("offense", "clarity", goal))

    # scramble/obfuscate -> offense.scrambler
    if any(k in g for k in ("scramble", "rot", "obfuscat")):
        steps.append(("offense", "scrambler", goal))

    # establish access / compose drafts quietly -> infiltrate
    if any(k in g for k in ("sneak", "stealth", "inside", "access", "compose", "draft", "infiltrate")):
        steps.append(("infiltrate", None, goal))

    # block/intervene/guard -> intervene
    if any(k in g for k in ("block", "intervene", "guard", "defense", "halt", "deny", "stop")):
        steps.append(("intervene", None, goal))

    # sensible default
    if not steps:
        steps.append(("offense", "clarity", goal))

    return steps

def _describe_step(i: int, mod: str, sub: Optional[str], payload: str) -> str:
    label = mod + (f".{sub}" if sub else "")
    prev = (payload or "").strip()
    if len(prev) > 60:
        prev = prev[:57] + "..."
    return f"{i}. {label} :: '{prev}'"

# -------------------- public entrypoint --------------------
def run(text: str = "", **kwargs) -> Dict[str, Any]:
    """
    Autonomy entrypoint.
    Accepts:
      - free text: 'auto write a clear summary'
      - 'plan: <goal>' or 'auto: <goal>'
      - explicit chain: 'chain: offense.echo -> offense.clarity -> intervene'
    Returns a structured dict with plan + per-step results.
    """
    goal = (text or kwargs.get("payload") or "").strip()
    if not goal:
        return {"status": "error", "reason": "empty goal", "module": "autonomy"}

    # strip common prefixes (auto:, autonomy:, plan:, chain:)
    for tag in ("auto:", "autonomy:", "plan:", "chain:"):
        if goal.lower().startswith(tag):
            goal = goal[len(tag):].strip()
            break

    mode, explicit = _parse_chain(goal)
    if mode == "explicit":
        steps = [(m, s, goal) for (m, s, _) in explicit]
    else:
        steps = _heuristic_plan(goal)

    # respect allowlist
    steps = [(m, s, p) for (m, s, p) in steps if m in CFG["allow_modules"]]

    plan_text = "\n".join(_describe_step(i + 1, m, s, goal) for i, (m, s, _) in enumerate(steps))
    print("autonomy plan:\n" + (plan_text or "[empty plan]"))

    _remember(f"auto goal: {goal}", tags=["auto", "goal"], importance=0.8)

    if CFG["require_approval"]:
        ans = input("[autonomy] approve plan? (y/n) ").strip().lower()
        if ans not in ("y", "yes"):
            _remember(f"auto aborted: {goal}", tags=["auto", "aborted"])
            return {"status": "aborted", "module": "autonomy", "goal": goal, "steps": [], "results": []}

    results: List[Dict[str, Any]] = []
    for idx, (mod_name, subtool, payload) in enumerate(steps, 1):
        mod = _import_module(mod_name)
        if not mod:
            results.append({"module": mod_name, "error": "import failed"})
            continue

        # pass subtool hint via conventional header in payload
        actual_payload = payload if not subtool else f"{subtool} :: {payload}"
        print(f"[autonomy] EXEC -> {mod_name}.run(...)")
        out = _run_module(mod, actual_payload)

        results.append({
            "module": mod_name,
            "subtool": subtool,
            "result": out,
        })

        _remember(f"auto exec {mod_name}", tags=["auto", "exec", mod_name], importance=0.6)

        if CFG["pause_ms"]:
            time.sleep(CFG["pause_ms"] / 1000.0)

        if CFG["require_approval"] and idx < len(steps):
            ans = input("[autonomy] continue? (y/n) ").strip().lower()
            if ans not in ("y", "yes"):
                _remember("auto halted mid-chain", tags=["auto", "halted"])
                break

    report = {
        "status": "ok",
        "module": "autonomy",
        "mode": mode,
        "goal": goal,
        "plan": [{"module": m, "subtool": s} for (m, s, _) in steps],
        "results": results,
        "arsenal": "42::autonomy.v1",
    }

    _remember("auto complete", tags=["auto", "done"])
    print("[INFO] autonomy: completed")
    return report