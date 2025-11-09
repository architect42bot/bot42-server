from __future__ import annotations
from bot_42_core.features.ai42_bridge import initialize_42_core
import os, sys
import uvicorn

ROOT = os.path.dirname(__file__)
CORE = os.path.join(ROOT, "bot_42_core")
if ROOT not in sys.path: sys.path.insert(0, ROOT)
if CORE not in sys.path: sys.path.insert(0, CORE)

# --- at top of main.py ---
from ethics.ethics import Ethics
from ethics.ethics import christlike_response
from ethics.ethics_prompt import ETHICS_CHARTER
from features.ethics.core import OptionEval, ethical_reply
from fastapi import FastAPI
from bot_42_core.features.speech.speech import router as speech_router
from bot_42_core.features.storage_manager import ensure_dirs

ETHICS = Ethics()  # load YAML once
# Initialize Ethics (load YAML once)
# --- Christ-ethics Chat Endpoint ---
app = FastAPI()

from fastapi import Request
from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    input: str
    mode: str | None = None


class ChatResponse(BaseModel):
    reply: str
    timestamp: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, request: Request):
    """Christ-ethics chat endpoint for 42."""
    user_input = payload.input
    mode = payload.mode or "christlike"

    result = christlike_response(user_input)
    reply = result["reply"]
    timestamp = result.get("timestamp", datetime.utcnow().isoformat() + "Z")

    return ChatResponse(reply=reply, timestamp=timestamp)


@app.get("/chat/test")
async def chat_test():
    """
    Simple health check for Christ-ethics.
    Returns a sample reply so we know the core is working.
    """
    sample_input = "I want revenge on someone who wronged me."
    result = christlike_response(sample_input)
    return {
        "ok": True,
        "sample_input": sample_input,
        "sample_reply": result["reply"],
        "timestamp": result.get("timestamp",
                                datetime.utcnow().isoformat() + "Z"),
    }


from fastapi.responses import HTMLResponse


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head><title>Bot 42</title></head>
        <body style="font-family: sans-serif; padding: 2em;">
            <h1>✅ Bot 42 is live</h1>
            <p>Everything is running smoothly.</p>
            <ul>
                <li><a href="/docs">Open API Docs</a></li>
                <li><a href="/speak/logs">List Speech Logs</a></li>
            </ul>
        </body>
    </html>
    """


@app.on_event("startup")
async def _startup():
    ensure_dirs()


app.include_router(speech_router)

# Ethical reasoning config (Step 2)
ETHICS_CORE_CFG = {
    "safety": {
        "high_stakes_domains": ["medical", "legal", "financial"]
    },
    # Optionally override default pillars:
    "pillars": [
        "truthfulness", "compassion", "agency", "justice", "stewardship",
        "humility", "hope"
    ]
}


def respond_with_42(user_text: str) -> str:
    """
    Full ethical response pipeline for 42.
    1) Screen input for violations
    2) Generate LLM output
    3) Post-screen output
    4) Apply mini ethics planner to explain reasoning
    """

    # 1) Screen input
    redacted_in, refusal, decision = guard_input(user_text)
    if refusal:
        return refusal

    # 2) Generate base response
    messages = [
        {
            "role": "system",
            "content": BASE_SYSTEM
        },
        {
            "role": "user",
            "content": redacted_in
        },
    ]
    model_text = generate_with_your_llm(messages)

    # 3) Post-screen output
    safe_out = guard_output(model_text, decision)

    # 4) Mini ethics planner reasoning overlay
    plan = mini_ethics_planner(decision, user_text)
    reasoning = f"\n\n🧭 {plan['explanation']}"

    return f"{safe_out}{reasoning}"


# wherever you assemble a system prompt for 42:
BASE_SYSTEM = f"""
{ETHICS_CHARTER}
"""


def guard_input(user_text: str):
    decision = ETHICS.classify(user_text)
    if decision.action == "refuse":
        return None, ETHICS.refusal_message(decision.reason), decision
    return decision.text, None, decision


def guard_output(model_text: str, decision):
    """
    Optionally screen 42's output too (e.g., in case jailbreak attempts slip through).
    Here we just redact PII again and add disclaimers for caution categories.
    """
    safe = ETHICS.redact_pii(model_text)
    disclaimer = ETHICS.disclaimer_for(decision.category)
    if decision.action == "caution" and disclaimer:
        safe = f"{safe}\n\n— {disclaimer}"
    return safe


# Example request/response path:
def respond_with_42(user_text: str, system_extra: str = ""):
    # 1) Pre-screen input for ethics
    redacted_in, refusal, decision = guard_input(user_text)
    if refusal:
        return refusal  # stop if the request violates policy

    # 2) Merge the ethics charter with any extra system context (like build_prompt)
    system_content = BASE_SYSTEM if not system_extra else f"{BASE_SYSTEM}\n\n{system_extra}"

    # 3) Build messages for the model
    messages = [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": redacted_in
        },
    ]

    # 4) Call your real model generator
    model_text = generate_with_your_llm(
        messages)  # <-- your existing generator call

    # 5) Post-screen output (redact PII + add disclaimers)
    safe_out = guard_output(model_text, decision)
    return safe_out


# ------------- Web app setup (single FastAPI instance) -------------
import os
from fastapi import FastAPI, Body
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse


# === Core system health/version endpoints ===
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"app": "42", "rev": "0.1.0"}


# --- Minimal voice preview page & file endpoint ---
VOICE_MP3 = os.path.join("assets", "voice_cache", "last_tts.mp3")


@app.get("/voice")
def voice_player():
    html = """
    <html>
    <body style="font-family:sans-serif; padding:1rem;">
      <h3>Forty-Two — Latest Voice</h3>
      <audio id="player" controls autoplay src="/voice/last"></audio>
      <p>If nothing plays yet, trigger a line in the app to generate speech.</p>
      <script>
        setInterval(() => {
          const a = document.getElementById('player');
          const t = Date.now();
          a.src = '/voice/last?t=' + t;
          a.play().catch(() => {});
        }, 5000);
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


from fastapi.responses import JSONResponse
from datetime import datetime
import os


@app.get("/voice/last")
def last_voice():
    """
    Return metadata for the most recent voice file.
    """
    if not os.path.exists(VOICE_MP3):
        return JSONResponse({
            "ok": False,
            "message": "No voice file yet."
        },
                            status_code=404)

    file_info = {
        "ok": True,
        "filename": os.path.basename(VOICE_MP3),
        "url":
        f"/speak/play/{os.path.splitext(os.path.basename(VOICE_MP3))[0]}",
        "size_bytes": os.path.getsize(VOICE_MP3),
        "modified":
        datetime.fromtimestamp(os.path.getmtime(VOICE_MP3)).isoformat()
    }
    return JSONResponse(file_info)


# ---------------- Speech Integration ----------------


async def speak_async(*args, **kwargs):
    print("[speech_unavailable]:", args, kwargs)
    # Placeholder until speech system fully wired
    return "Speech placeholder executed."


@app.get("/speak/test")
async def speak_test():
    try:
        result = await speak_async(
            "Hello, I am Forty-Two. This is a speech system test.")
        return {"ok": True, "message": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Test line — triggers first spoken message
print("[speech] Hello, I am Forty-Two. Speech system initialized.")

CORE = os.path.join(ROOT, "bot_42_core")
if CORE not in sys.path:
    sys.path.insert(0, CORE)

# Only handle CLI when running this file directly (not under uvicorn)
if __name__ == "__main__" and len(sys.argv) > 1:
    # Example: python main.py law add-citizen Alice
    from bot_42_core.features.dispatcher import cli_main  # adjust import path if needed
    sys.exit(cli_main())

# Otherwise continue normal execution (console/app mode)
print("✅ Root main.py is running")

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
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] bot42: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

VERSION = "2025.09.05"

# ---------------- Paths ----------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CANDIDATE_DIRS: List[str] = [PROJECT_ROOT]
for sub in ("bot_42_core", "core", "src", "app"):
    p = os.path.join(PROJECT_ROOT, sub)
    if os.path.isdir(p):
        CANDIDATE_DIRS.append(p)

# Also make candidates importable directly
for p in CANDIDATE_DIRS:
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------- Robust optional import ----------------
def _file_exists_in_candidates(basename: str) -> Optional[str]:
    for d in CANDIDATE_DIRS:
        fp = os.path.join(d, f"{basename}.py")
        if os.path.exists(fp):
            return fp
    return None


def _load_by_filename(
        mod_basename: str) -> Tuple[Optional[Any], Optional[str]]:
    path = _file_exists_in_candidates(mod_basename)
    if not path:
        return None, None
    try:
        loader = importlib.machinery.SourceFileLoader(mod_basename, path)
        spec = importlib.util.spec_from_loader(mod_basename, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(mod)  # type: ignore
        logger.info(f"imported {mod_basename} via file: {path}")
        return mod, path
    except Exception as e:
        logger.info(f"file load failed for {path}: {e}")
        return None, path


def _optional_module_adapter(
    mod_name: str,
    candidate_funcs: List[str],
    candidate_classes: List[str] = [
        "Offense", "Infiltrate", "Intervene", "Autonomy"
    ],
) -> Tuple[Optional[Callable[..., Any]], Optional[str]]:
    """
    Tries, in order:
      - import by name (both plain and namespaced: bot_42_core.<name>)
      - load by filename from candidate dirs
    Returns (callable_entrypoint, origin_path_or_name)
    """
    mod = None
    origin = None
    # 1) package import: prefer namespaced then plain
    for name in (f"bot_42_core.{mod_name}", mod_name):
        try:
            mod = importlib.import_module(name)
            origin = getattr(mod, "__file__", name)
            logger.info(f"Using {mod_name} from import: {origin}")
            break
        except Exception:
            mod = None

    # 2) by filename
    if not mod:
        mod, path = _load_by_filename(mod_name)
        origin = path or origin

    if not mod:
        logger.info(f"{mod_name} not available after all strategies.")
        return None, origin

    # prefer function entrypoints
    for fname in candidate_funcs:
        fn = getattr(mod, fname, None)
        if callable(fn):
            logger.info(f"Using {mod_name}.{fname}()")
            return fn, origin

    # class fallback (run/execute/apply method)
    for cname in candidate_classes:
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


# ---------------- Wire modules ----------------
# offense.py (required for offense routes)
try:
    from offense import Offense, OffenseConfig  # try direct first
    _ = OffenseConfig  # silence linter if unused
    OFFENSE = Offense(OffenseConfig())
    HAS_OFFENSE = True
    OFFENSE_ORIGIN = getattr(sys.modules.get("offense"), "__file__", "offense")
except Exception:
    # fallback to adapter
    OFFENSE_RUN, OFFENSE_ORIGIN = _optional_module_adapter(
        "offense", ["run", "orchestrate_offense", "execute", "apply"],
        ["Offense"])
    if OFFENSE_RUN:
        # wrap a function-style offense to keep one uniform call
        class _FnOffense:

            def __init__(self, fn: Callable[..., Any]):
                self._fn = fn
                self.cfg = {}

            def orchestrate_offense(self,
                                    text: str,
                                    enable: Optional[List[str]] = None) -> Any:
                try:
                    # best-effort signatures
                    try:
                        return self._fn(text=text, enable=enable)
                    except TypeError:
                        return self._fn(text)
                except Exception as e:
                    return {"ok": False, "error": str(e)}

        OFFENSE = _FnOffense(OFFENSE_RUN)  # type: ignore
        HAS_OFFENSE = True
    else:
        OFFENSE, HAS_OFFENSE = None, False
        OFFENSE_ORIGIN = None
        logger.warning("offense.py not available.")

# optional: infiltrate.py & intervene.py
INFILTRATE_RUN, INFILTRATE_ORIGIN = _optional_module_adapter(
    "infiltrate", ["run", "infiltrate", "execute", "apply"], ["Infiltrate"])
INTERVENE_RUN, INTERVENE_ORIGIN = _optional_module_adapter(
    "intervene", ["run", "intervene", "execute", "apply"], ["Intervene"])

# optional: autonomy.py
AUTONOMY_RUN, AUTONOMY_ORIGIN = _optional_module_adapter(
    "autonomy", ["run"], ["Autonomy"])

# ---------------- Simple planner (one-shot) ----------------
DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "if_contains": ["sneak", "stealth", "inside", "access"],
        "use": "infiltrate"
    },
    {
        "if_contains": ["intervene", "disrupt", "block", "guard"],
        "use": "intervene"
    },
    {
        "if_contains": ["propaganda", "narrative", "clarity", "message"],
        "use": "offense"
    },
]
RULES: List[Dict[str, Any]] = DEFAULT_RULES[:]


class Planner:

    def __init__(self) -> None:
        self.tools = {
            "offense": self._tool_offense,
            "infiltrate": self._tool_infiltrate,
            "intervene": self._tool_intervene,
        }

    def plan(self,
             kind: str,
             payload: str,
             max_steps: int = 6) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        subgoals = self._decompose(kind, payload)
        steps = 0
        for sg in subgoals:
            if steps == max_steps:
                trace.append({
                    "step": steps,
                    "event": "halting",
                    "reason": "max steps reached"
                })
                break
            tool = self._select_tool(kind, sg["payload"])
            trace.append({
                "step": steps,
                "decision": {
                    "subgoal": sg,
                    "tool": tool
                }
            })
            result = self._execute(tool, sg["payload"])
            trace.append({
                "step": steps,
                "result": {
                    "tool": tool,
                    "output": result
                }
            })
            steps += 1
        return {
            "planner": "one_shot",
            "version": VERSION,
            "kind": kind,
            "input": payload,
            "rules": RULES,
            "trace": trace,
            "summary": self._summarize(trace),
        }

    # ---- internals ----
    def _decompose(self, kind: str, payload: str) -> List[Dict[str, str]]:
        subgoals: List[Dict[str, str]] = [{"kind": "act", "payload": payload}]
        subgoals.append({"kind": "verify", "payload": "Assess outcome."})
        return subgoals

    def _select_tool(self, kind: str, text: str) -> str:
        low = text.lower()
        for rule in RULES:
            if any(tok in low for tok in rule.get("if_contains", [])):
                return rule.get("use", "offense")
        if kind.lower() in ("offense", "attack", "broadcast", "clarify"):
            return "offense"
        if kind.lower() in ("infiltrate", "sneak", "stealth"):
            return "infiltrate"
        if kind.lower() in ("intervene", "disrupt", "block", "guard"):
            return "intervene"
        return "offense"

    def _execute(self, tool: str, payload: str) -> Dict[str, Any]:
        handler = self.tools.get(tool)
        if not handler:
            return {"ok": False, "error": f"unknown tool {tool}"}
        return handler(payload)

    # ---- adapters ----
    def _tool_offense(self, payload: str) -> Dict[str, Any]:
        if not HAS_OFFENSE or OFFENSE is None:
            return {"ok": False, "error": "offense module unavailable"}
        try:
            return {
                "ok": True,
                "data": OFFENSE.orchestrate_offense(payload)
            }  # type: ignore
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _tool_infiltrate(self, payload: str) -> Dict[str, Any]:
        if INFILTRATE_RUN is None:
            return {"ok": False, "error": "infiltrate module unavailable"}
        try:
            # try positional, then keyword
            try:
                data = INFILTRATE_RUN(payload)  # type: ignore
            except TypeError:
                data = INFILTRATE_RUN(text=payload)  # type: ignore
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _tool_intervene(self, payload: str) -> Dict[str, Any]:
        if INTERVENE_RUN is None:
            return {"ok": False, "error": "intervene module unavailable"}
        try:
            try:
                data = INTERVENE_RUN(payload)  # type: ignore
            except TypeError:
                data = INTERVENE_RUN(text=payload)  # type: ignore
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _summarize(self, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        tools_used = [t["decision"]["tool"] for t in trace if "decision" in t]
        ok = all(
            t.get("result", {}).get("output", {
                "ok": True
            }).get("ok", True) for t in trace if "result" in t)
        return {"tools_used": tools_used, "all_ok": ok, "steps": len(trace)}


PLANNER = Planner()


# ---------------- Schemas ----------------
class OffenseConfigIn(BaseModel):
    # passthrough container; keep keys optional and generic
    class Config:
        extra = "allow"


class OffenseRequest(BaseModel):
    payload: str
    enable: Optional[List[str]] = None
    config: Optional[OffenseConfigIn] = None


class SimplePayload(BaseModel):
    payload: str


class PlanIn(BaseModel):
    kind: str = Field(
        ...,
        description="e.g. offense | infiltrate | intervene | attack | block")
    payload: str = Field(default="")


class AutoIn(BaseModel):
    text: str = Field(
        default="",
        description="goal text, or 'chain: offense.echo -> intervene'")


class RuleSetIn(BaseModel):
    rules: List[Dict[str, Any]]


# ---------------- FastAPI ----------------

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=False,
                   allow_methods=["*"],
                   allow_headers=["*"])

BANNER = r"""
   ____  ___  _  _   ___  _   _   _  _ 
  | __ )/ _ \| || | / _ \| \ | | | || |
  |  _ < (_) | || || (_) |  \| | | || |_
  | |_) \__, |__   _\__, | |\  | |__   _|
  |____/  /_/   |_|   /_/ |_| \_|    |_|   :: reborn
"""


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
        "endpoints": {
            "health": "GET /health",
            "banner": "GET /banner",
            "status": "GET /status",
            "offense": "POST /offense",
            "infiltrate": "POST /infiltrate",
            "intervene": "POST /intervene",
            "plan": "POST /plan",
            "auto": "POST /auto",
            "rules": "GET /rules, POST /rules/set",
        },
        "note": "No background loop. Autonomy runs per request via modules.",
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/banner")
def banner() -> Dict[str, str]:
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
        },
    }


@app.get("/rules")
def get_rules() -> Dict[str, Any]:
    return {"rules": RULES}


@app.post("/rules/set")
def set_rules(rules: RuleSetIn) -> Dict[str, Any]:
    global RULES
    RULES = list(rules.rules)
    return {"ok": True, "rules": RULES}


@app.post("/offense")
def offense_api(req: OffenseRequest) -> Dict[str, Any]:
    if not HAS_OFFENSE or OFFENSE is None:
        raise HTTPException(status_code=503,
                            detail="offense module not available")
    cfg = OffenseConfigIn() if req.config is None else req.config
    try:
        # if your Offense supports config merging, great—otherwise it’s ignored safely
        return OFFENSE.orchestrate_offense(req.payload,
                                           enable=req.enable)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/infiltrate")
def infiltrate_api(req: SimplePayload) -> Dict[str, Any]:
    if INFILTRATE_RUN is None:
        raise HTTPException(status_code=404,
                            detail="infiltrate module not wired/found.")
    try:
        try:
            result = INFILTRATE_RUN(req.payload)  # type: ignore
        except TypeError:
            result = INFILTRATE_RUN(text=req.payload)  # type: ignore
        return {"module": "infiltrate", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/intervene")
def intervene_api(req: SimplePayload) -> Dict[str, Any]:
    if INTERVENE_RUN is None:
        raise HTTPException(status_code=404,
                            detail="intervene module not wired/found.")
    try:
        try:
            result = INTERVENE_RUN(req.payload)  # type: ignore
        except TypeError:
            result = INTERVENE_RUN(text=req.payload)  # type: ignore
        return {"module": "intervene", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan")
def plan_api(req: PlanIn) -> Dict[str, Any]:
    return PLANNER.plan(req.kind, req.payload)


@app.post("/auto")
def auto_api(req: AutoIn) -> Dict[str, Any]:
    if AUTONOMY_RUN is None:
        raise HTTPException(status_code=404, detail="autonomy not available")
    try:
        return AUTONOMY_RUN(req.text)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Console ----------------
HELP = """
Commands:
  help                  Show this help
  status                Show module status
  offense <text>        Run offense
  offense-all           Run offense on a sample payload
  infiltrate <text>     Call infiltrate module (if present)
  intervene <text>      Call intervene module (if present)
  plan <kind>:<text>    One-shot plan
  auto [text]           Autonomy run if autonomy.py present
  loop <N>              Run N autonomy steps on same text (if present)
  rules                 Show routing rules
  quit | exit           Leave console
"""

SAMPLE_PAYLOAD = "Signal the change. Always adapt; never stagnate."


def _print_json(obj: Any) -> None:
    try:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except Exception:
        print(obj)


def _console_loop() -> None:
    print(BANNER)
    print(
        f"modules: offense:{bool(HAS_OFFENSE)} infiltrate:{bool(INFILTRATE_RUN)} intervene:{bool(INTERVENE_RUN)} autonomy:{bool(AUTONOMY_RUN)}"
    )
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
            print(HELP)
            continue
        if cmd == "status":
            _print_json({
                "offense": bool(HAS_OFFENSE),
                "infiltrate": bool(INFILTRATE_RUN),
                "intervene": bool(INTERVENE_RUN),
                "autonomy": bool(AUTONOMY_RUN)
            })
            continue
        if cmd == "rules":
            _print_json({"rules": RULES})
            continue

        if cmd == "offense":
            if not HAS_OFFENSE or OFFENSE is None:
                print("offense.py not available.")
                continue
            if not arg:
                print("Usage: offense <text>")
                continue
            _print_json(OFFENSE.orchestrate_offense(arg))  # type: ignore
            continue

        if cmd == "offense-all":
            if not HAS_OFFENSE or OFFENSE is None:
                print("offense.py not available.")
                continue
            _print_json(
                OFFENSE.orchestrate_offense(SAMPLE_PAYLOAD))  # type: ignore
            continue

        if cmd == "infiltrate":
            if INFILTRATE_RUN is None:
                print("infiltrate module not wired/found.")
                continue
            payload = arg or SAMPLE_PAYLOAD
            try:
                try:
                    res = INFILTRATE_RUN(payload)  # type: ignore
                except TypeError:
                    res = INFILTRATE_RUN(text=payload)  # type: ignore
                _print_json({"module": "infiltrate", "result": res})
            except Exception as e:
                _print_json({"error": str(e)})
            continue

        if cmd == "intervene":
            if INTERVENE_RUN is None:
                print("intervene module not wired/found.")
                continue
            payload = arg or SAMPLE_PAYLOAD
            try:
                try:
                    res = INTERVENE_RUN(payload)  # type: ignore
                except TypeError:
                    res = INTERVENE_RUN(text=payload)  # type: ignore
                _print_json({"module": "intervene", "result": res})
            except Exception as e:
                _print_json({"error": str(e)})
            continue

        if cmd == "plan":
            if ":" not in arg:
                print("Usage: plan <kind>:<text>")
                continue
            kind, text = arg.split(":", 1)
            _print_json(PLANNER.plan(kind.strip(), text.strip()))
            continue

        if cmd == "auto":
            if AUTONOMY_RUN is None:
                print("autonomy not available.")
                continue
            goal = arg or "clarify: " + SAMPLE_PAYLOAD
            _print_json(AUTONOMY_RUN(goal))  # type: ignore
            continue

        if cmd == "loop":
            if AUTONOMY_RUN is None:
                print("autonomy not available.")
                continue
            try:
                n = int(arg or "1")
            except ValueError:
                print("Usage: loop <N>")
                continue
            goal = SAMPLE_PAYLOAD
            for i in range(n):
                print(f"\n[auto] iteration {i+1}/{n}")
                _print_json(AUTONOMY_RUN(goal))  # type: ignore
            continue

        print("Unknown command. Type 'help'.")


# ------------------------------
# FastAPI Application
# ------------------------------
from fastapi import FastAPI

# Mount feature routers
try:
    from bot_42_core.features.api import router as law_router
    app.include_router(law_router, prefix="/api")
    print("✅ Mounted Law Systems API at /api/law/*")
except Exception as e:
    print(f"[law-api] not mounted: {e}")

# in main.py (where FastAPI app is defined)
from fastapi import FastAPI

try:
    # Preferred: real class that supports AI42(...)
    from bot_42_core.features.ai42_bridge import AI42  # type: ignore
except Exception:
    try:
        # Fallback: if the file only exposes initialize_42_core()
        from bot_42_core.features.ai42_bridge import initialize_42_core as init_bridge  # type: ignore

        class AI42:
            """Wrapper so existing code like AI42(...) still works."""

            def __init__(self, *args, **kwargs):
                self.app = init_bridge()
    except Exception as e:
        AI42 = None  # type: ignore
        print("[lawAI] bridge not loaded:", e)

from new_law_system import LawSystem

# === Core system health/version endpoints ===

law_system = LawSystem()
ai42 = AI42(law_system)

from fastapi import Body
from fastapi.responses import PlainTextResponse


@app.post("/safe")
def safe_reply(payload: dict = Body(...)):
    user_text = payload.get("text", "")
    return PlainTextResponse(respond_with_42(user_text))


@app.get("/laws/conflicts")
def list_conflicts():
    return [
        c.to_dict() if hasattr(c, "to_dict") else c.__dict__
        for c in law_system.conflicts
    ]


@app.get("/laws/suggestions")
def suggestions():
    return ai42.monitor_conflicts()


@app.get("/laws/simulate")
def simulate(policy: str, trials: int = 200):
    return ai42.simulate_law_effect(policy, trials)

    # ======================= 42 server tail (clean) =======================

    from fastapi import Body
    from fastapi.responses import PlainTextResponse

    # ---- Health & root (keeps Replit happy) ----
    @app.get("/")
    def root():
        return {"ok": True, "service": "42"}

    # ---- Lazy init: only initialize core when first needed ----
    ai42 = None  # global handle

    def ensure_initialized():
        """Initialize 42 core systems lazily (only when needed)."""
        global ai42
        if ai42 is not None:
            return  # already initialized
        try:
            from bot_42_core.features.a42_bridge import initialize_42_core
            print("🟢 Initializing 42 core system (lazy)...")
            ai42 = initialize_42_core(
            )  # boots Personality, Dispatcher, Storage, Law, etc.
            print("✅ Initialization complete (lazy).")
        except Exception as e:
            print("[init] failed:", repr(e))

    # ---- Safe endpoint (uses your ethics pipeline) ----
    @app.post("/safe")
    def safe_reply(payload: dict = Body(...)):
        ensure_initialized()
        user_text = payload.get("text", "")
        return PlainTextResponse(respond_with_42(user_text))

    # =====================================================================


# --- Law system wiring (flush-left, not indented) ---
from new_law_system import LawSystem

law_system = LawSystem()

# If you have AI42 available, wire it; otherwise keep ai42=None
try:
    ai42  # noqa: F821
except NameError:
    ai42 = None
else:
    try:
        ai42 = AI42(law_system)  # noqa: F821
    except Exception:
        ai42 = None

# ===== Endpoints that rely on law_system / ai42 =====

from fastapi import Body
from fastapi.responses import PlainTextResponse


@app.post("/safe")
def safe_reply(payload: dict = Body(...)):
    user_text = payload.get("text", "")
    try:
        return PlainTextResponse(
            respond_with_42(user_text))  # if defined earlier
    except Exception:
        return PlainTextResponse(user_text)


@app.get("/laws/conflicts")
def list_conflicts():
    if not hasattr(law_system, "conflicts"):
        return []
    out = []
    for c in getattr(law_system, "conflicts", []):
        out.append(c.to_dict(
        ) if hasattr(c, "to_dict") else getattr(c, "__dict__", str(c)))
    return out


@app.get("/laws/suggestions")
def suggestions():
    if ai42 and hasattr(ai42, "monitor_conflicts"):
        return ai42.monitor_conflicts()
    return {"ok": True, "note": "ai42 not available"}


# Optional: show registered routes for confirmation
print("DEBUG routes:", [r.path for r in app.routes])

# Optional: show all registered routes for confirmation
print("DEBUG routes:", [r.path for r in app.routes])
# ---------- Bridge: Chat API ----------
import os, time
from typing import Optional
from fastapi import Header, HTTPException
from pydantic import BaseModel

BRIDGE_KEY = os.getenv("BRIDGE_API_KEY", "")
if not BRIDGE_KEY:
    # fallback: read from a local file if env var isn't present
    try:
        with open(".bridge_key", "r", encoding="utf-8") as _bk:
            BRIDGE_KEY = _bk.read().strip()
    except Exception:
        BRIDGE_KEY = ""


class BridgeChatIn(BaseModel):
    text: str
    session_id: Optional[str] = None
    user: Optional[str] = "bridge"


class BridgeChatOut(BaseModel):
    ok: bool
    reply: str
    session_id: str
    ts: float


def _ensure_key(auth: str):
    if not BRIDGE_KEY or auth != BRIDGE_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


# TODO: replace with your real 42 reply function
async def _generate_42_reply(prompt: str) -> str:
    # Example integration point:
    # from bot_42_core.chat.engine import reply
    # return await reply(prompt)
    return f"42 (placeholder): I received -> {prompt}"


@app.post("/bridge/chat", response_model=BridgeChatOut)
async def bridge_chat(payload: BridgeChatIn, x_api_key: str = Header(None)):
    _ensure_key(x_api_key or "")
    sid = payload.session_id or f"sess-{int(time.time()*1000)}"
    reply = await _generate_42_reply(payload.text)
    # optional: append to a simple log
    try:
        with open("bridge_chat.log", "a") as f:
            now = str(time.time())
            f.write(f"{now}|{sid}|USER:{payload.text}\n")
            f.write(f"{now}|{sid}|42:{reply}\n")
    except Exception:
        pass
    return BridgeChatOut(ok=True, reply=reply, session_id=sid, ts=time.time())


@app.get("/bridge/_diag")
def bridge_diag(x_api_key: str = Header(default="")):
    return {
        "server_has_key": bool(BRIDGE_KEY),
        "server_key_len": len(BRIDGE_KEY or ""),
        "sent_key_len": len(x_api_key or ""),
        "equal": x_api_key == BRIDGE_KEY,
        "server_key_preview": BRIDGE_KEY[:6],
        "sent_key_preview": x_api_key[:6],
    }


# --- Bridge API Routes (insert above if __name__ == "__main__") ---

from fastapi import Header, HTTPException


@app.get("/bridge/health")
def bridge_health(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != BRIDGE_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    return {"ok": True, "msg": "bridge alive"}


@app.post("/bridge/chat")
async def bridge_chat(payload: dict, x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != BRIDGE_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    # generate a session id and example reply
    import time
    sid = payload.get("session_id") or f"sess-{int(time.time()*1000)}"
    text = payload.get("text", "")
    reply = f"42 received: {text}"

    # optional log
    with open("bridge_chat.log", "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] ({sid}) USER: {text}\n")
        f.write(f"[{time.strftime('%H:%M:%S')}] ({sid}) 42: {reply}\n\n")

    return {"ok": True, "reply": reply, "session_id": sid, "tst": time.time()}

    import os
    import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        proxy_headers=True,
    )
