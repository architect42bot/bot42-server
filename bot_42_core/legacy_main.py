
# main.py
# 42 :: CORE (API + Console + Optional Autonomy) — Python 3.10+
# Safe loader that discovers modules in the cwd and bot_42_core/

from __future__ import annotations
print("✅ Running root-level main.py")

import json
import logging
import os
import sys
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import importlib
import importlib.util
import importlib.machinery

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------- Logging ----------------
logger = logging.getLogger("bot42")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

VERSION = "2025.09.05"

# ------------- Paths & Robust Import -------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CANDIDATE_DIRS: List[str] = [PROJECT_ROOT]
for sub in ("bot_42_core", "core", "src", "app"):
    p = os.path.join(PROJECT_ROOT, sub)
    if os.path.isdir(p):
        CANDIDATE_DIRS.append(p)

# de-dupe while preserving order
_seen = set()
CANDIDATE_DIRS = [d for d in CANDIDATE_DIRS if d not in _seen and not _seen.add(d)]


def _file_exists_in_candidates(basename: str) -> Optional[str]:
    """
    Return first file path that exists among candidate dirs for given basename (without .py).
    """
    for d in CANDIDATE_DIRS:
        fp = os.path.join(d, f"{basename}.py")
        if os.path.exists(fp):
            return fp
    return None


def _load_module_by_filename(mod_basename: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Attempt to load module from a discovered filename.
    """
    path = _file_exists_in_candidates(mod_basename)
    if not path:
        return None, None
    try:
        loader = importlib.machinery.SourceFileLoader(mod_basename, path)
        spec = importlib.util.spec_from_loader(mod_basename, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(mod)  # type: ignore
        logger.info(f"Loaded {mod_basename} from file: {path}")
        return mod, path
    except Exception as e:
        logger.info(f"File load failed for {path}: {e}")
        return None, path


def optional_module_adapter(
    mod_name: str,
    candidate_funcs: List[str],
) -> Tuple[Optional[Callable[..., Any]], Optional[str]]:
    """
    Try standard import; fallback to loading by filename from candidate dirs.
    Return (callable_entrypoint, origin_path).
    """
    origin: Optional[str] = None
    mod: Optional[Any] = None

    # Strategy 1: normal import
    try:
        mod = importlib.import_module(mod_name)
        origin = getattr(mod, "__file__", None)
        logger.info(f"Imported {mod_name} via sys.path ({origin})")
    except Exception as e:
        logger.info(f"{mod_name} not importable via sys.path: {e}")

    # Strategy 2: by filename
    if mod is None:
        mod, origin = _load_module_by_filename(mod_name)

    if mod is None:
        logger.info(f"{mod_name} not available after all strategies.")
        return None, origin

    # Prefer direct function names
    for fname in candidate_funcs:
        fn = getattr(mod, fname, None)
        if callable(fn):
            logger.info(f"Using {mod_name}.{fname}()")
            return fn, origin

    # Fallback: class-based run/execute/apply on default class names
    for cname in ("Intervene", "Infiltration", "Infiltrate", "Offense", "Autonomy"):
        cls = getattr(mod, cname, None)
        if cls:
            try:
                inst = cls()  # type: ignore
                for m in ("run", "execute", "apply"):
                    meth = getattr(inst, m, None)
                    if callable(meth):
                        logger.info(f"Using {mod_name}.{cname}.{m}()")
                        return meth, origin
            except Exception as e:
                logger.info(f"{mod_name}.{cname} init failed: {e}")

    logger.info(f"{mod_name} loaded but no compatible entrypoint found.")
    return None, origin


# ------------- offense.py (required/recommended) -------------
try:
    from offense import Offense, OffenseConfig  # resolved via PROJECT_ROOT on sys.path
    OFFENSE = Offense(OffenseConfig())
    HAS_OFFENSE = True
    OFFENSE_ORIGIN = getattr(sys.modules.get("offense"), "__file__", None)
except Exception as e:
    logger.warning(f"offense.py not available: {e}")
    OFFENSE = None  # type: ignore
    HAS_OFFENSE = False
    OFFENSE_ORIGIN = None

# ------------- Optional modules (infiltrate.py, intervene.py, autonomy.py) -------------
INFILTRATE_RUN, INFILTRATE_ORIGIN = optional_module_adapter(
    "infiltrate", ["run", "infiltrate", "execute", "apply"]
)
INTERVENE_RUN, INTERVENE_ORIGIN = optional_module_adapter(
    "intervene", ["run", "intervene", "execute", "apply"]
)
AUTONOMY_RUN, AUTONOMY_ORIGIN = optional_module_adapter(
    "autonomy", ["run", "execute", "apply"]
)

# ------------- FastAPI App -------------
app = FastAPI(title="42 :: Core", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BANNER = r"""
   ___  _   _   _  _  ___   ___
  / _ \| | | | | || || __| / __|
 | (_) | |_| | | __ || _|  \__ \
  \__\_\\___/  |_||_||___| |___/
"""

# ------------- Schemas -------------
class OffenseConfigIn(BaseModel):
    pulse_marker: Optional[str] = None
    pulse_step: Optional[int] = Field(default=None, ge=1)
    pulse_key: Optional[int] = None
    echo_phrases: Optional[List[str]] = None
    echo_gain: Optional[float] = None
    scramble_rot: Optional[int] = Field(default=None, ge=0, le=26)
    purge_list: Optional[List[str]] = None
    normalize_replacements: Optional[Dict[str, str]] = None
    brittle_rules: Optional[List[str]] = None
    contradiction_pairs: Optional[List[List[str]]] = None

    def merge_into(self, cfg: "OffenseConfig") -> "OffenseConfig":
        # Only set provided fields to preserve defaults on the engine
        if self.pulse_marker is not None: cfg.pulse_marker = self.pulse_marker
        if self.pulse_step   is not None: cfg.pulse_step   = int(self.pulse_step)
        if self.pulse_key    is not None: cfg.pulse_key    = int(self.pulse_key)
        if self.echo_phrases is not None: cfg.echo_phrases = list(self.echo_phrases)
        if self.echo_gain    is not None: cfg.echo_gain    = float(self.echo_gain)
        if self.scramble_rot is not None: cfg.scramble_rot = int(self.scramble_rot)
        if self.purge_list   is not None: cfg.purge_list   = list(self.purge_list)
        if self.normalize_replacements is not None:
            cfg.normalize_replacements = dict(self.normalize_replacements)
        if self.brittle_rules is not None:
            cfg.brittle_rules = list(self.brittle_rules)
        if self.contradiction_pairs is not None:
            cfg.contradiction_pairs = [tuple(p) for p in self.contradiction_pairs if len(p) == 2]
        return cfg


class OffenseRequest(BaseModel):
    payload: str
    enable: Optional[List[str]] = None
    config: Optional[OffenseConfigIn] = None


class SimplePayload(BaseModel):
    payload: str


class AutoIn(BaseModel):
    text: str = Field(default="")  # accepts "plan: ..." | "auto: ..." | "chain: ..."


# ------------- API Routes -------------
@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": "42 :: Core",
        "version": VERSION,
        "modules": {
            "offense": HAS_OFFENSE,
            "infiltrate": INFILTRATE_RUN is not None,
            "intervene": INTERVENE_RUN is not None,
            "autonomy": AUTONOMY_RUN is not None,
        },
        "note": "No background loop. Each call runs once.",
        "endpoints": {
            "health": "GET /health",
            "banner": "GET /banner",
            "status": "GET /status",
            "offense": "POST /offense",
            "infiltrate": "POST /infiltrate",
            "intervene": "POST /intervene",
            "auto": "POST /auto",
        },
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/banner")
def banner() -> Dict[str, Any]:
    return {"banner": BANNER, "version": VERSION}


@app.get("/status")
def status() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "cwd": os.getcwd(),
        "project_root": PROJECT_ROOT,
        "candidate_dirs": CANDIDATE_DIRS,
        "modules": {
            "offense": HAS_OFFENSE,
            "infiltrate": INFILTRATE_RUN is not None,
            "intervene": INTERVENE_RUN is not None,
            "autonomy": AUTONOMY_RUN is not None,
            "origin": {
                "offense": OFFENSE_ORIGIN,
                "infiltrate": INFILTRATE_ORIGIN,
                "intervene": INTERVENE_ORIGIN,
                "autonomy": AUTONOMY_ORIGIN,
            },
        },
    }


@app.post("/offense")
def run_offense(req: OffenseRequest) -> Dict[str, Any]:
    if not HAS_OFFENSE or OFFENSE is None:
        raise HTTPException(status_code=503, detail="offense module not available")
    cfg = OffenseConfig()
    if req.config is not None:
        cfg = req.config.merge_into(cfg)
    engine = Offense(cfg)
    result = engine.orchestrate_offense(req.payload, enable=req.enable)
    return result


@app.post("/infiltrate")
def run_infiltrate(req: SimplePayload) -> Dict[str, Any]:
    if INFILTRATE_RUN is None:
        raise HTTPException(status_code=404, detail="infiltrate module not wired/found.")
    try:
        res = INFILTRATE_RUN(req.payload)  # type: ignore
    except TypeError:
        res = INFILTRATE_RUN(payload=req.payload)  # type: ignore
    return {"module": "infiltrate", "result": res}


@app.post("/intervene")
def run_intervene(req: SimplePayload) -> Dict[str, Any]:
    if INTERVENE_RUN is None:
        raise HTTPException(status_code=404, detail="intervene module not wired/found.")
    try:
        res = INTERVENE_RUN(req.payload)  # type: ignore
    except TypeError:
        res = INTERVENE_RUN(payload=req.payload)  # type: ignore
    return {"module": "intervene", "result": res}


@app.post("/auto")
def run_auto(req: AutoIn) -> Dict[str, Any]:
    if AUTONOMY_RUN is None:
        raise HTTPException(status_code=404, detail="autonomy module not wired/found.")
    text = req.text or ""
    try:
        out = AUTONOMY_RUN(text)  # prefer positional
    except TypeError:
        out = AUTONOMY_RUN(text=text)  # keyword fallback
    return {"module": "autonomy", "result": out}


# ------------- Console -------------
HELP = """
Commands:
  help                 Show this help
  status               Show module status
  offense <text>       Run offense on <text>
  offense-all          Run offense on a sample payload
  infiltrate <text>    Call infiltrate module (if present)
  intervene  <text>    Call intervene module (if present)
  auto [text]          Autonomy entrypoint (plan/auto/chain accepted)
  quit | exit          Leave console
"""

SAMPLE_PAYLOAD = (
    "Signal the change. Always adapt; never stagnate. The AL-GOR-ITHM binds the machine."
)

def _print_json(obj: Any) -> None:
    try:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except Exception:
        print(obj)


def _console_loop() -> None:
    print("modules:",
          f"offense:{HAS_OFFENSE}",
          f"infiltrate:{INFILTRATE_RUN is not None}",
          f"intervene:{INTERVENE_RUN is not None}",
          f"autonomy:{AUTONOMY_RUN is not None}")
    print("Type 'help' for commands.\n")

    while True:
        try:
            line = input("42> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye_.")
            break

        if not line:
            continue

        cmd, *rest = line.split(" ", 1)
        arg = rest[0].strip() if rest else ""

        if cmd in ("quit", "exit"):
            print("bye_.")
            break

        if cmd == "help":
            print(HELP); continue

        if cmd == "status":
            _print_json(status()); continue

        if cmd == "offense":
            if not HAS_OFFENSE or OFFENSE is None:
                print("offense.py not available."); continue
            if not arg:
                print("Usage: offense <text>"); continue
            _print_json(OFFENSE.orchestrate_offense(arg)); continue

        if cmd == "offense-all":
            if not HAS_OFFENSE or OFFENSE is None:
                print("offense.py not available."); continue
            _print_json(OFFENSE.orchestrate_offense(SAMPLE_PAYLOAD)); continue

        if cmd == "infiltrate":
            if INFILTRATE_RUN is None:
                print("infiltrate module not wired/found."); continue
            payload = arg or SAMPLE_PAYLOAD
            try:
                res = INFILTRATE_RUN(payload)  # type: ignore
            except TypeError:
                res = INFILTRATE_RUN(payload=payload)  # type: ignore
            _print_json({"module": "infiltrate", "result": res}); continue

        if cmd == "intervene":
            if INTERVENE_RUN is None:
                print("intervene module not wired/found."); continue
            payload = arg or SAMPLE_PAYLOAD
            try:
                res = INTERVENE_RUN(payload)  # type: ignore
            except TypeError:
                res = INTERVENE_RUN(payload=payload)  # type: ignore
            _print_json({"module": "intervene", "result": res}); continue

        if cmd == "auto":
            if AUTONOMY_RUN is None:
                print("autonomy module not wired/found."); continue
            text = arg or "plan: clarify this text"
            try:
                res = AUTONOMY_RUN(text)  # type: ignore
            except TypeError:
                res = AUTONOMY_RUN(text=text)  # type: ignore
            _print_json({"module": "autonomy", "result": res}); continue

        print("Unknown command. Type 'help'.")


# ------------- Entrypoint -------------
if __name__ == "__main__":
    # Always use python3.
    if "--console" in sys.argv:
        _console_loop()
    elif "--demo" in sys.argv:
        if HAS_OFFENSE and OFFENSE:
            print(json.dumps(OFFENSE.orchestrate_offense(SAMPLE_PAYLOAD),
                             indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"error": "offense.py not available"}, indent=2))
    else:
        print("This file provides the FastAPI `app` and the console (`--console`).")
        print("Run console: python3 main.py --console")
        print("Run API:     python3 -m uvicorn main:app --host=0.0.0.0 --port=8000 --reload")