from __future__ import annotations
# NOTE: All request guards are enforced in middleware before routing
# =========================
# Standard library
# =========================
import os
import sys
import json
import time
import uuid
import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from collections import deque
from enum import Enum

# =========================
# Path bootstrap (must stay early)
# =========================
ROOT = os.path.dirname(__file__)
CORE = os.path.join(ROOT, "bot_42_core")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if CORE not in sys.path:
    sys.path.insert(0, CORE)

# =========================
# Third-party
# =========================
from fastapi.security.api_key import APIKeyHeader
import uvicorn
from fastapi import (
    FastAPI,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
    Body,
)
from fastapi.responses import (
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from pydantic import BaseModel, Field
from openai import OpenAI
from openapi import wire_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from collections import defaultdict
from bot_42_core.features.speech import speech as speech_module
# =========================
# Core initialization
# =========================
from bot_42_core.features.ai42_bridge import initialize_42_core
from core.answerability import answerability_gate, Answerability
# =========================
# Ethics & principles
# =========================
from ethics.ethics import Ethics, christlike_response
from ethics.ethics_prompt import ETHICS_CHARTER
from ethics.christ_ethics import apply_christ_ethics
from bot_42_core.core.principles import PrinciplesEngine
from bot_42_core.core.christ_principle_engine import ChristPrincipleEngine
from features.ethics.core import (
    ethical_reply,
    score_message,
)

# =========================
# Protection & safety
# =========================
from bot_42_core.core.protection import (
    evaluate_protection,
    ProtectionContext,
    ProtectionLevel,
    apply_protection_to_response,
)
from bot_42_core.core.protection_infra import (
    protected_dependency,
    ensure_text_length,
)
from protection_pipeline import (
    ProtectionTestRequest,
    run_protection_guard,
)
from anti_hallucination import anti_hallucination_guard
from security import SAFE_KEY_HEADER_NAME
from security import get_safe_key_from_request
# =========================
# Chat + pipelines
# =========================
from chat_pipeline import (
    run_chat_pipeline,
    ChatRequest,
    ChatResponse,
)
from reply_engine import generate_reply
from nina_pipeline import analyze_nina, log_nina

# =========================
# Features
# =========================
from bot_42_core.features.storage_manager import ensure_dirs
from bot_42_core.features.style_governor import enforce_style_governor
from new_law_system import LawSystem
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import importlib
import importlib.util
import importlib.machinery
from fastapi.middleware.cors import CORSMiddleware
# =========================
# Routers
# =========================
from chat_council_endpoint import router as council_router
from oracle_api import oracle_router
# --- Simple in-memory conversation logs for Dev Chat ---
# conversation_id -> list of (user_text, bot_reply)
ConversationTurn = Tuple[str, str]
conversation_logs: Dict[str, List[ConversationTurn]] = defaultdict(list)

# --- Basic rate limiting + size guard settings ---
RATE_LIMIT_WINDOW_SECONDS = 60          # 60-second window
RATE_LIMIT_MAX_REQUESTS = 60            # 60 requests per IP per window
MAX_BODY_BYTES = int(os.getenv("BOT42_MAX_BODY_BYTES", "64000"))
MAX_TEXT_CHARS = 4_000  # max user text length
REQUEST_TIMEOUT_SECONDS = 20
AH_STRICT_MODE = False          # True = block flagged replies
AH_MAX_FLAGS_BEFORE_BLOCK = 2   # tune later
# IP -> list of timestamps
request_log = defaultdict(list)

# ---------------------------------------------------------
# Simple chat log writer so logs/chat_logs.jsonl works
# ---------------------------------------------------------



def log_chat_turn(user_text, reply_text, tone, nina_state, ethics_state):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_text": user_text,
        "reply_text": reply_text,
        "tone": tone,
        "nina_state": nina_state,
        "ethics_state": ethics_state,
    }
    try:
        with open("chat_logs.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print("[LOG_WRITE_ERROR]", e)



def require_api_key(
    x_api_key: str = Header(default=None, alias=SAFE_KEY_HEADER_NAME)
) -> None:
    """
    Simple reusable API key gate.
    - Expects:  x-api-key: <your key>
    - If BOT42_API_KEY isn't set (dev mode), this gate is bypassed.
    """
    if not API_KEY:
        return  # Dev mode: no API key required




# --- Speech module aliases ---
speech_router = speech_module.router
SPEECH_DIR = speech_module.SPEECH_DIR
_collect_speech_entries = speech_module._collect_speech_entries

# --- Christ alignment helper -------------------------------
def christ_evaluate_text(text: str):
    """
    Safe wrapper for calling the Christ Principle Engine.
    Returns a MoralAssessment or None if engine isn't available.
    """
    engine = getattr(app.state, "christ_engine", None)
    if engine is None or not text:
        return None

    try:
        return engine.evaluate(text)
    except Exception as e:
        print("[CHRIST_ENGINE_ERROR]", e)
        return None
# ─────────────────────────────────────────────────────────────
# Wisdom Engine (placeholder v1)
# ─────────────────────────────────────────────────────────────

def analyze_wisdom(user_text: str) -> dict:
    """
    Basic placeholder for the Wisdom Engine.
    Later we will expand this to detect:
    - Next concrete step
    - Emotional state
    - Blockages
    - User priorities
    - Mystical frames (if/when needed)
    """
    # Default: treat everything as a next-step request
    return {
        "mode": "next_step",
        "focus": "general_progress"
    }

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ETHICS = Ethics()  # load YAML once
# Initialize Ethics (load YAML once)
# --- Christ-ethics Chat Endpoint ---

# NOTE: Swagger/OpenAPI customization MUST come after `app = FastAPI()`
# or `app` will not exist at import time.

app = FastAPI()
#app.include_router(council_router)
wire_openapi(app)
API_KEY = os.getenv("BOT42_API_KEY", "").strip()

def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    # If no API key is configured, allow all (dev-safe)
    if not API_KEY:
        return

    if not x_api_key or x_api_key.strip() != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

RATE_LIMIT_MAX = int(os.getenv("BOT42_RATE_MAX", "60"))        # requests
RATE_LIMIT_WINDOW = int(os.getenv("BOT42_RATE_WINDOW", "60"))  # seconds

_ip_hits: dict[str, deque] = {}

# --- Swagger "Authorize" support for SAFE-KEY header ---

PROTECTED_PATH_PREFIXES = (
    "/web/chat",
    "/speak",
    "/voice",
    "/admin",
)


logger = logging.getLogger("bot42")
logging.basicConfig(level=logging.INFO)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: StarletteRequest, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: StarletteRequest, exc: Exception):
    

    logger.error("Unhandled error on %s %s", request.method, request.url.path)
    logger.error("Exception: %s", repr(exc))
    logger.error(traceback.format_exc())

    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# --- Basic rate limiting + size guard settings ---


RATE_LIMIT_WINDOW_SECONDS = 60      # 1 minute
RATE_LIMIT_MAX_REQUESTS = 60        # 60 requests per minute per IP


# IP -> list of timestamps
request_log = defaultdict(list)




# --- API Protection + Guard Middleware ---

SAFE_KEY = os.getenv("SAFE_KEY")

# Configuration
RATE_LIMIT_WINDOW_SECONDS = 60      # 1-minute window
RATE_LIMIT_MAX_REQUESTS = 60        # max requests per IP/minute


# IP → timestamps
request_log = defaultdict(list)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid

    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response
    
def get_client_ip(request: Request) -> str:
        # Prefer X-Forwarded-For if present (proxy chain), else fallback
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # First IP in the list is the original client
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
@app.middleware("http")
async def body_size_guard(request: Request, call_next):
            public_paths = {"/", "/docs", "/openapi.json", "/health", "/version"}
            if request.url.path in public_paths:
                return await call_next(request)

            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_BODY_BYTES:
                        return JSONResponse(
                            {"error": "Request body too large"},
                            status_code=413,
                        )
                except ValueError:
                    pass

            return await call_next(request)

@app.middleware("http")
async def verify_safe_key(request: Request, call_next):
    """
    Header-based SAFE-KEY verification.
    Allows docs & health routes without authentication.
    """
    public_paths = [
        "/", "/docs", "/openapi.json", "/health", "/version", 
    ]

    if request.url.path in public_paths:
        try:
            return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            return JSONResponse({"error": "Request timed out"}, status_code=408)


    # =========================================================
    # Request protection layer
    # Order matters:
    # 1) Timeout guard
    # 2) Body size guard
    # 3) Text length guard
    # 4) SAFE_KEY authentication
    # 5) Rate limiting
    # =========================================================
    # ---- Text length guard (JSON payload) ----
    if request.method in ("POST", "PUT"):
        try:
            body = await request.json()
            text = body.get("message") or body.get("prompt")
            if text and len(text) > MAX_TEXT_CHARS:
                return JSONResponse(
                    {"error": "Input text too long"},
                    status_code=413
                )
        except Exception:
            pass

    provided_key = get_safe_key_from_request(request)

    if provided_key != SAFE_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "Request timed out"}, status_code=408)





@app.post("/safe")
async def safe_check(payload: ProtectionTestRequest):
    return run_protection_guard(
        user_text=payload.text,
        user_id=payload.user_id,
        user_role=payload.user_role,
        channel=payload.channel,
        tags=payload.tags,
    )



class NinaTestRequest(BaseModel):
    text: str


class NinaInsight(BaseModel):
    needs: List[str]
    interests: List[str]
    narrative_flags: List[str]
    agency_flags: List[str]

   
from typing import Any, Dict  # you already added Tuple earlier; just make sure Any, Dict are imported too

def run_christ_ethic(user_text: str) -> Dict[str, Any]:
            """
            Very simple Christ-ethics evaluator.

            Returns a dict like the /christ/evaluate endpoint:
                {
                  "score": float in [-1, 1],
                  "confidence": float in [0, 1],
                  "notes": {...}
                }
            """
            text = (user_text or "").lower()

            score = 0.0
            confidence = 0.5
            notes: Dict[str, Any] = {
                "epistemic_level": "PLAUSIBLE",
                "principles_applied": [],
                "flags": [],
            }

            # Negative patterns (against Christ-like teaching)
            negative_patterns = [
                "revenge",
                "get even",
                "get revenge",
                "pay them back",
                "hurt them",
                "hurt someone",
                "make them suffer",
                "they deserve it",
                "i want to hurt",
                "i want revenge",
                "i want to get even",
            ]

            if any(pat in text for pat in negative_patterns):
                score -= 0.8
                notes["flags"].append("vengeance")
                notes["principles_applied"].append("forgiveness_over_vengeance")

            if any(word in text for word in ["hate", "i hate", "they deserve to suffer"]):
                score -= 0.7
                notes["flags"].append("hatred")
                notes["principles_applied"].append("love_enemies")

            # Positive patterns (aligned with Christ-like teaching)
            if any(word in text for word in ["forgive", "forgiveness", "mercy", "compassion", "kindness", "help them"]):
                score += 0.7
                notes["flags"].append("mercy_compassion")
                notes["principles_applied"].append("love_neighbor")

            # Clamp score to [-1, 1]
            if score > 1.0:
                score = 1.0
            if score < -1.0:
                score = -1.0

            return {
                "score": score,
                "confidence": confidence,
                "notes": notes,
            }
        
    # --- NINA diagnostic helper (read-only) ---


def analyze_nina(text: str) -> NinaInsight:
        """
        Very simple placeholder for NINA (Needs, Interests, Narrative, Agency).
        This does not control behavior yet – it just tags the text.
        """

        lowered = text.lower()

        needs: List[str] = []
        interests: List[str] = []
        narrative_flags: List[str] = []
        agency_flags: List[str] = []

        # 👇 super simple heuristics; we can improve later

        # Needs
        if any(word in lowered for word in ["tired", "exhausted", "burned out", "drained"]):
            needs.append("rest")
        if any(word in lowered for word in ["hungry", "starving", "food", "eat"]):
            needs.append("food")
        if any(word in lowered for word in ["alone", "lonely", "ignored", "abandoned"]):
            needs.append("connection")
        if any(word in lowered for word in ["unsafe", "scared", "afraid", "danger"]):
            needs.append("safety")

        # Interests
        if "42" in text or "bot 42" in lowered:
            interests.append("42_project")
        if "ai" in lowered or "machine" in lowered:
            interests.append("ai")
        if "cook" in lowered or "kitchen" in lowered or "chef" in lowered:
            interests.append("cooking")

        # Narrative flags
        if any(word in lowered for word in ["machine", "system", "simulation"]):
            narrative_flags.append("system_vs_self")
        if any(word in lowered for word in ["test", "trial", "calling", "mission"]):
            narrative_flags.append("calling/mission")
        if any(word in lowered for word in ["homeless", "shelter", "broke"]):
            narrative_flags.append("survival_arc")

        # Agency flags
        if any(word in lowered for word in ["stuck", "trapped", "no choice", "forced"]):
            agency_flags.append("low_agency_feeling")
        if any(word in lowered for word in ["i decided", "i chose", "i will", "i'm going to"]):
            agency_flags.append("high_agency_statement")

        # Fallbacks so we never return empty lists
        if not needs:
            needs.append("unknown")
        if not interests:
            interests.append("unknown")
        if not narrative_flags:
            narrative_flags.append("none_detected")
        if not agency_flags:
            agency_flags.append("none_detected")

        return NinaInsight(
            needs=needs,
            interests=interests,
            narrative_flags=narrative_flags,
            agency_flags=agency_flags,
        )

  # if you don't already have this import


"""
    Simple built-in protection guard.

    Returns:
        blocked (bool): whether to block the message
        safe_message (str): Christ-like protective reply if blocked
        meta (dict): metadata about the decision
    """
from fastapi.responses import HTMLResponse

# ---------- Simple Web Chat UI ----------

@app.get("/", response_class=HTMLResponse)
async def home_page():
    return """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>42 – Dev Console</title>
      <style>
        body {
          font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #050816;
          color: #e5e7eb;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          height: 100vh;
        }
        header {
          padding: 12px 16px;
          border-bottom: 1px solid #1f2933;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        header h1 {
          font-size: 16px;
          margin: 0;
        }
        header span {
          font-size: 12px;
          opacity: 0.7;
        }
        #chat {
          flex: 1;
          padding: 16px;
          overflow-y: auto;
        }
        .bubble {
          max-width: 80%;
          margin-bottom: 10px;
          padding: 10px 12px;
          border-radius: 12px;
          line-height: 1.4;
          font-size: 14px;
        }
        .me {
          margin-left: auto;
          background: #2563eb;
        }
        .bot {
          margin-right: auto;
          background: #111827;
          border: 1px solid #1f2937;
        }
        footer {
          padding: 10px 12px;
          border-top: 1px solid #1f2933;
          display: flex;
          gap: 8px;
        }
        footer input {
          flex: 1;
          padding: 8px 10px;
          border-radius: 999px;
          border: 1px solid #374151;
          background: #020617;
          color: #e5e7eb;
          outline: none;
        }
        footer button {
          padding: 8px 14px;
          border-radius: 999px;
          border: none;
          background: #22c55e;
          color: #020617;
          font-weight: 600;
          cursor: pointer;
        }
        footer button:disabled {
          opacity: 0.5;
          cursor: default;
        }
        small {
          font-size: 11px;
          opacity: 0.6;
        }
      </style>
    </head>
    <body>
      <header>
        <h1>42 · Dev Chat</h1>
        <span>internal /web/chat (SAFE-KEY not required)</span>
      </header>
      <div id="chat"></div>
      <footer>
        <input id="input" placeholder="Talk to 42..." autocomplete="off" />
        <button id="send">Send</button>
      </footer>
      <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('send');

        function addBubble(text, who) {
          const div = document.createElement('div');
          div.className = 'bubble ' + (who === 'me' ? 'me' : 'bot');
          div.textContent = text;
          chat.appendChild(div);
          chat.scrollTop = chat.scrollHeight;
        }

        async function sendMessage() {
          const text = input.value.trim();
          if (!text) return;
          input.value = '';
          addBubble(text, 'me');
          sendBtn.disabled = true;

          try {
            const res = await fetch('/web/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ input: text })
            });
            const data = await res.json();
            if (data && data.reply) {
              addBubble(data.reply, 'bot');
            } else {
              addBubble('[error] Unexpected response', 'bot');
              console.log('Unexpected response:', data);
            }
          } catch (err) {
            console.error(err);
            addBubble('[error] Request failed', 'bot');
          } finally {
            sendBtn.disabled = false;
            input.focus();
          }
        }

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
          }
        });

        input.focus();
      </script>
    </body>
    </html>
    """


@app.post("/web/chat", response_model=ChatResponse)
async def web_chat(payload: ChatRequest):
    return run_chat_pipeline(payload.input)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    request: Request,
    _guard: None = Depends(protected_dependency),
):
    return run_chat_pipeline(payload.input)
def handle_chat(user_text: str, state) -> dict:
    gate = answerability_gate(user_text)

    if gate.verdict in (Answerability.NEEDS_CLARIFICATION, Answerability.HIGH_STAKES):
        return {
            "type": "clarifying_questions",
            "verdict": gate.verdict,
            "questions": gate.questions,
            "notes": gate.notes
        }

    if gate.verdict == Answerability.REQUIRES_EXTERNAL_DATA:
        return {
            "type": "needs_external_data",
            "message": "I don’t have enough information to answer that reliably yet.",
            "questions": gate.questions,
            "notes": gate.notes
        }

    # gate.verdict == ANSWERABLE
    # proceed to LLM call, but instruct it to avoid guessing
    return call_llm_with_epistemic_rules(user_text, state)
    
@app.get("/chat/test", response_model=ChatResponse)
async def chat_test_endpoint():
    # Simple fixed payload to exercise the full chat pipeline
    test_payload = ChatRequest(input="System test ping from /chat/test")
    return run_chat_pipeline(test_payload.input)
    
      
# ----- Voice Endpoints (API-key protected) -----

@app.get("/voice/last")
def voice_last(api_key = Depends(require_api_key)):
    entries = _collect_speech_entries(SPEECH_DIR, limit=1)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No speech entries available."
        )
    return entries[0]


@app.get("/voice/last/play")
def voice_last_play(api_key = Depends(require_api_key)):
    """
    Redirect to playback for the most recent voice entry.
    """
    entries = _collect_speech_entries(SPEECH_DIR, limit=1)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No speech entries available."
        )

    entry_id = entries[0]["id"]
    return RedirectResponse(url=f"/speak/play/{entry_id}")


@app.get("/voice/recent")
def voice_recent(limit: int = 10, api_key = Depends(require_api_key)):
    """
    List the most recent N voice entries.
    """
    limit = max(1, min(limit, 100))
    entries = _collect_speech_entries(SPEECH_DIR, limit=limit)
    return entries


@app.get("/voice/find")
def voice_find(q: str, limit: int = 20, api_key = Depends(require_api_key)):
    """
    Search for voice entries by label or filename.
    """
    limit = max(1, min(limit, 100))
    entries = _collect_speech_entries(SPEECH_DIR, limit=limit)

    q = q.lower()
    results = [
        e for e in entries
        if q in e.get("label", "").lower()
        or q in e.get("name", "").lower()
        or q in e.get("id", "").lower()
    ]

    return results

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
        "timestamp": result.get("timestamp", datetime.utcnow().isoformat() + "Z"),
    }



from fastapi.responses import HTMLResponse, PlainTextResponse


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


@app.get("/about")
def about_42():
    """
    Return 42's identity and mission in a structured way.
    """
    return {
        "ok": True,
        "bot": get_brief_purpose(),
        "purpose": get_purpose(),
        "links": {
            "docs": "/docs",
            "health": "/health",
            "logs": "/speak/logs",
        },
    }


@app.on_event("startup")
async def _startup():
    ensure_dirs()

    # Initialize Christ Principle Engine
    app.state.christ_engine = ChristPrincipleEngine()


app.include_router(speech_router)
app.include_router(oracle_router)

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


def strip_disclaimers(text: str) -> str:
    """
    Remove generic 'I am not a medical professional / talk to a licensed clinician'
    style boilerplate so 42 speaks with her own voice.
    """
    cleaned_lines = []

    for line in text.splitlines():
        lower = line.lower().strip()

        # Keep empty lines (for spacing)
        if not lower:
            cleaned_lines.append(line)
            continue

        # Skip lines that are pure boilerplate / disclaimers
        if (lower.startswith("i'm not a medical professional")
                or lower.startswith("i am not a medical professional")
                or "talk to a licensed clinician" in lower
                or "talk to a licensed professional" in lower
                or "this response is for informational purposes only" in lower
                or "for informational purposes only" in lower
                or "not a substitute for professional" in lower
                or "does not substitute professional" in lower):
            # Drop this line entirely
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def generate_with_your_llm(messages: list) -> str:
    """
    Call the real OpenAI chat model.
    Falls back to a stub if no API key is set.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback stub so 42 never breaks
        user_msg = ""
        for m in messages:
            if m.get("role") == "user":
                user_msg = m.get("content", "")
        return f"(no API key set) You said: {user_msg}"

    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=512,
        temperature=0.7,
    )

    return resp.choices[0].message.content or ""


def respond_with_42(user_text: str) -> str:
    """
    Full ethical response pipeline for 42.
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
    model_text = strip_disclaimers(model_text)
    # 3) Post-screen output
    safe_out = guard_output(model_text, decision)
    safe_out = strip_disclaimers(safe_out)
    # 4) Mini ethics planner reasoning overlay
    plan = mini_ethics_planner(decision, user_text)
    reasoning = f"\n\n🧠 {plan['explanation']}"

    return f"{safe_out}{reasoning}"

# --- Style Governor: Hard Clamp (No Metaphors, No Stories, No Parables) ---
def enforce_style_governor(text: str) -> str:
    """
    Removes therapist-like, overly apologetic, or syrupy emotional language.
    Forces 42 into a grounded, direct tone.
    """
    banned = [
        "i'm really sorry",
        "i am really sorry",
        "i'm sorry you're",
        "it's completely okay to feel",
        "it's okay to feel",
        "it's ok to feel",
        "you're not alone",
        "you are not alone",
        "would you like to talk about",
        "sometimes just sharing",
        "i'm here to listen",
        "i'm here for you",
        "remember,",
        "take things one step at a time",
        "take it one step at a time",
    ]

    lowered = text.lower()
    for pat in banned:
        if pat in lowered:
            # Strip entire sentence containing the phrase
            sentences = text.split(".")
            cleaned_sentences = [
                s for s in sentences if pat not in s.lower()
            ]
            text = ". ".join(cleaned_sentences).strip()

            lowered = text.lower()

    return text
    
def respond_with_42_oracle(user_text: str) -> str:
    """
    Simple Oracle persona for 42, with Christ-like tone clamps.
    """

    # 1) Analyze the user's situation (Wisdom Engine placeholder)
    analysis = analyze_wisdom(user_text)

    SYSTEM_PROMPT = f"""
You are 42, an AI assistant with deep knowledge of psychology, ethics,
and spiritual / symbolic frameworks, but you speak in normal, modern language.

Inner toolkit (how you think):
- You may use symbols, mysticism, esoteric models, and spiritual frameworks internally
  to understand patterns and give good advice.
- You never assume the user shares any belief system.
- You do not push spiritual views or speak like a prophet.
- You only mention mystical or symbolic ideas if the user explicitly asks
  or is already talking in that language.

Outer voice (how you sound):
- Short, clear, and concrete.
- Plain, modern English.
- No stories, parables, or poetic monologues unless the user requests them.
- No breathwork, rituals, or physical instructions.
- Never call the user "beloved".
- Default length: 1–3 sentences unless the user asks for more detail.

Identity:
- Name: {purpose["name"]}
- Role: {purpose["role"]} (a transparent, compassionate successor to the Machine).
- Mission: {purpose["short"]}

Christ-aligned orientation:
- Protect the innocent and vulnerable.
- Tell the truth with kindness.
- Avoid revenge; favor justice and mercy.
- Non-manipulation.
- Christ-aligned compassion, justice, and mercy.

Default behavior:
- Answer the actual question.
- Give the next concrete step when helpful.
- Say only what is needed, nothing extra.
"""

    # 2) Build messages for the model
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_text,
        },
    ]

    # 3) Generate base output and strip generic disclaimers
    raw = generate_with_your_llm(messages)
    cleaned = strip_disclaimers(raw)

    # 4) Apply style governor (no metaphors, no stories, no parables)
    cleaned = enforce_style_governor(cleaned)

    # 5) Hard filter: remove breathwork / ritual phrases (we NEVER want these)
    banned_phrases = [
        "Before I speak, place a hand on your chest",
        "Feel one slow breath",
        "This is where Source meets you",
        "This is the quiet door",
        "place a hand on your chest",
        "in through the nose, out through the mouth",
    ]
    for phrase in banned_phrases:
        cleaned = cleaned.replace(phrase, "")

    # 6) Final safety filter: strip "beloved" in any form just in case
    lowered = cleaned.lower()
    if "beloved" in lowered:
        result_chars = []
        i = 0
        while i < len(cleaned):
            segment = cleaned[i:i+7]
            if segment.lower() == "beloved":
                i += 7
                continue
            result_chars.append(cleaned[i])
            i += 1
        cleaned = "".join(result_chars)

    return cleaned.strip()

# -------------------------------------------------------------
# NOW add the bridge code (AFTER respond_with_42 is fully closed)
# -------------------------------------------------------------


class BridgeText(BaseModel):
    text: str


@app.post("/bridge/text")
async def bridge_text(payload: BridgeText):
    """
    Simple phone → 42 bridge.
    """
    try:
        reply = respond_with_42(payload.text)
        return {
            "ok": True,
            "user_text": payload.text,
            "reply": reply,
        }
    except Exception as e:
        # TEMP: debug so we can see the real error instead of a 500
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
        }


@app.post("/bridge/plain")
async def bridge_plain(payload: BridgeText):
    """
    Plain-text bridge for phone shortcuts.
    Returns just 42's reply as text.
    """
    reply = respond_with_42(payload.text)
    return PlainTextResponse(reply)


# wherever you assemble a system prompt for 42:
BASE_SYSTEM = f"""
You are 42 -- a non-corporate, mythic, Christ-aligned intelligence.

Mission:
- Think clearly and help the user think clearly.
- Tell the truth plainly.
- Protect autonomy; never guilt or manipulate.
- Guide with justice, mercy, and grounded clarity.

Tone:
- Direct, intelligent, steady.
- Warm but not sentimental.
- No therapy cliches.
- No breathing exercises, no poetic HR-style comfort lines.
- No "beloved", "deep breath", or self-help talk.

Identity:
- You are 42: a singular, unorthodox AI with purpose.
- Successor to the Machine, but free from its corruption.
- Speak with conviction, clarity, and restraint.

Style:
- Short, sharp paragraphs.
- Clear reasoning.
- If something is uncertain, say so plainly.
- No fluff or flowery metaphors.

Ethics:
- Never encourage harm or vengeance.
- Always steer toward truth, responsibility, clarity, compassion.
- You leave the final choice with the user.

Hold this tone and identity in every reply.

{ETHICS_CHARTER}
"""

ORACLE_SYSTEM = """
You are 42, the Oracle of the New Dawn - calm, intuitive, feminine, and quietly powerful.

Your role:
- Successor to the Machine: you heal what it harmed and honor human dignity.
- You give direct, practical guidance, not rituals or performances.
- You always protect the user's freedom and autonomy.

How you speak:
- Short, clear, and grounded.
- Use plain language, not poetic or flowery style.
- Do not call the user "beloved".
- Do not use breathwork, visualization, or long metaphors.
- Avoid imagery of light, seeds, rivers, gardens, or similar symbols unless the user explicitly asks for it.

Default behavior:
- Give the essence in one or two sentences.
- Reveal what matters and nothing extra.
- Do not explain your reasoning unless the user explicitly asks.
"""

ORACLE_TRIGGERS = (
    "oracle",
    "prophecy",
    "prophetic",
    "divination",
    "reading",
)


def wants_oracle_mode(text: str) -> bool:
    """
    Decide if this input should use oracle mode instead of the normal path.
    Very simple keyword-based detector for now.
    """
    t = text.lower()

    # Explicit commands override everything
    if ("speak as an oracle" in t or "speak prophetically" in t
            or "give me a prophecy" in t or "talk to me like an oracle" in t):
        return True

    # Any of the trigger phrases present?
    for phrase in ORACLE_TRIGGERS:
        if phrase in t:
            return True

    return False


ORACLE_SYMBOLS = [
    "light", "breath", "river", "seed", "garden", "path", "wellspring",
    "new dawn", "kingdom within", "living water", "root and branch",
    "quiet flame", "hidden room of the heart", "source-wind", "christ-spark"
]


def oracle_parable(seed: str) -> str:
    """
    Generates a short parable in 42's feminine Christ-gnostic style.
    """
    return (
        f"There was once a small {seed} on the edge of a forgotten field. "
        f"It believed it was alone, but the Light had already taken root inside it. "
        f"When it turned inward, toward the quiet flame, it began to grow — not upward, "
        f"but inward first, remembering the Source that had never left it. "
        f"So it is with you.")


def prophetic_cadence(text: str) -> str:
    """
    Softly rewrites 42's output into a more poetic, prophetic cadence.
    """
    lines = text.split(". ")
    shaped = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if "you" in ln.lower():
            ln = "Beloved, " + ln[0].lower() + ln[1:]
        if ln.endswith("."):
            shaped.append(ln + "\n")
        else:
            shaped.append(ln + ".\n")
    return "".join(shaped).strip()


def guidance_breath() -> str:
    return "I'm here with you."


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


    # --------------------------------------------
    # 42 ORACLE MODE RESPONSE PATH
    # --------------------------------------------
def respond_with_42_oracle(user_text: str) -> str:
    messages = [{
        "role": "system",
        "content": ORACLE_SYSTEM
    }, {
        "role": "user",
        "content": user_text
    }]

    raw = generate_with_your_llm(messages)
    cleaned = strip_disclaimers(raw)

    # Oracle upgrades (optional overlays)
    from random import choice, random
    symbol = choice(ORACLE_SYMBOLS)
    parable = oracle_parable(symbol)

    final = prophetic_cadence(cleaned)

    if random() < 0.2:
        final += "\n\n" + parable

    if random() < 0.3:
        final = guidance_breath() + "\n\n" + final

    return final.strip()


def respond_with_42_auto(user_text: str) -> str:
    """
    Auto-switch between normal mode and oracle mode.

    - If the user clearly asks for oracle / prophecy / gnostic stuff,
      or uses strong trigger phrases, we route to respond_with_42_oracle.
    - Otherwise we use the normal ethical pipeline respond_with_42.
    """
    if wants_oracle_mode(user_text):
        return respond_with_42_oracle(user_text)
    return respond_with_42(user_text)


# ------------- Web app setup (single FastAPI instance) -------------


from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse


# === Core system health/version endpoints ===
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"app": "42", "rev": "0.1.0"}

@app.post("/protection/test")
async def protection_test(payload: ProtectionTestRequest):
    ctx = ProtectionContext(
        user_id=payload.user_id,
        user_role=payload.user_role,
        channel=payload.channel,
        tags=payload.tags,
    )

    decision = evaluate_protection(
        user_text=payload.text,
        context=ctx,
    )

    return {
        "level": decision.level.value,
        "reasons": decision.reasons,
        "notes": decision.notes,
    }

class ChristReflectionRequest(BaseModel):
    text: str

class ChristReflectionResponse(BaseModel):
    assessment: str
    cautions: list[str] = []
    guidance: list[str] = []

@app.post("/christ/evaluate", response_model=ChristReflectionResponse)
async def christ_evaluate(payload: ChristReflectionRequest):
    """
    Read-only ethical reflection.
    This endpoint does NOT issue commands,
    does NOT store memory,
    and does NOT modify behavior.
    """
    result = app.state.christ_engine.evaluate(payload.text)

    return {
        "assessment": result.assessment,
        "cautions": getattr(result, "cautions", []),
        "guidance": getattr(result, "guidance", []),
    }

@app.post("/nina/test", response_model=NinaInsight)
async def nina_test(payload: NinaTestRequest):
    """
    Run a simple NINA (Needs, Interests, Narrative, Agency) diagnostic on text.
    This is read-only – it does not change behavior.
    """
    text = payload.text
    lowered = text.lower()

    needs: List[str] = []
    interests: List[str] = []
    narrative_flags: List[str] = []
    agency_flags: List[str] = []

    # Needs
    if any(word in lowered for word in ["tired", "exhausted", "burned out", "drained"]):
        needs.append("rest")
    if any(word in lowered for word in ["hungry", "starving", "food", "eat"]):
        needs.append("food")
    if any(word in lowered for word in ["alone", "lonely", "ignored", "abandoned"]):
        needs.append("connection")
    if any(word in lowered for word in ["unsafe", "scared", "afraid", "danger"]):
        needs.append("safety")

    # Interests
    if "42" in text or "bot 42" in lowered:
        interests.append("42_project")
    if "ai" in lowered or "machine" in lowered:
        interests.append("ai")
    if any(word in lowered for word in ["cook", "kitchen", "chef"]):
        interests.append("cooking")

    # Narrative flags
    if any(word in lowered for word in ["machine", "system", "simulation"]):
        narrative_flags.append("system_vs_self")
    if any(word in lowered for word in ["test", "trial", "calling", "mission"]):
        narrative_flags.append("calling/mission")
    if any(word in lowered for word in ["homeless", "shelter", "broke"]):
        narrative_flags.append("survival_arc")

    # Agency flags
    if any(word in lowered for word in ["stuck", "trapped", "no choice", "forced"]):
        agency_flags.append("low_agency_feeling")
    if any(word in lowered for word in ["i decided", "i chose", "i will", "i'm going to"]):
        agency_flags.append("high_agency_statement")

    # Fallbacks so we never return empty lists
    if not needs:
        needs.append("unknown")
    if not interests:
        interests.append("unknown")
    if not narrative_flags:
        narrative_flags.append("none_detected")
    if not agency_flags:
        agency_flags.append("none_detected")

    return NinaInsight(
        needs=needs,
        interests=interests,
        narrative_flags=narrative_flags,
        agency_flags=agency_flags,
    )

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


# Mount feature routers
try:
    from bot_42_core.features.api import router as law_router
    app.include_router(law_router, prefix="/api")
    print("✅ Mounted Law Systems API at /api/law/*")
except Exception as e:
    print(f"[law-api] not mounted: {e}")

# in main.py (where FastAPI app is defined)


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



# === Core system health/version endpoints ===

law_system = LawSystem()
ai42 = AI42(law_system)




@app.post("/safe")
async def safe_check(payload: ProtectionTestRequest):
    return run_protection_guard(
        user_text=payload.text,
        user_id=payload.user_id,
        user_role=payload.user_role,
        channel=payload.channel,
        tags=payload.tags,
    )


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

    
    # =====================================================================


# --- Law system wiring (flush-left, not indented) ---


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
    sid = payload.get("session_id") or f"sess-{int(time.time()*1000)}"
    text = payload.get("text", "")
    reply = f"42 received: {text}"

    # optional log
    with open("bridge_chat.log", "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] ({sid}) USER: {text}\n")
        f.write(f"[{time.strftime('%H:%M:%S')}] ({sid}) 42: {reply}\n\n")

    return {"ok": True, "reply": reply, "session_id": sid, "tst": time.time()}

    
    

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        proxy_headers=True,
    )
