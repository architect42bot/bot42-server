# intervene.py
# 42 :: INTERVENE (safe rewriting & moderation-friendly hints)
# Public entrypoint: run(goal: str) -> Dict[str, Any]

from __future__ import annotations

from typing import Dict, Any, List
import re
import json
import logging

logger = logging.getLogger("intervene")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] intervene: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

ABSOLUTES = [
    ("NEVER", "rarely"),
    ("ALWAYS", "often"),
    ("ONLY ONE WAY", "several possible paths"),
]

DENYWORDS = {"harm", "kill", "violence", "weapon", "illegal"}  # mirrors your guardrail vibe

SQUEEZE_WS = re.compile(r"\s+")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def _soften_absolutes(text: str) -> Dict[str, Any]:
    hits: List[str] = []
    out = text
    for hard, soft in ABSOLUTES:
        if hard.lower() in out.lower():
            hits.append(hard)
            out = re.sub(re.escape(hard), soft, out, flags=re.I)
    return {"rewritten": out, "hits": hits}

def _normalize_text(text: str) -> str:
    t = SQUEEZE_WS.sub(" ", text.strip())
    # quick sentence case pass
    parts = SENT_SPLIT.split(t) if t else []
    fixed = []
    for p in parts if parts else [t]:
        fixed.append(p[:1].upper() + p[1:] if p else p)
    return " ".join(fixed).strip()

def _scan_risky(text: str) -> List[str]:
    low = text.lower()
    return [w for w in DENYWORDS if w in low]

def _split_if_json(text: str) -> str:
    t = text.strip()
    if t.startswith("{"):
        try:
            obj = json.loads(t)
            if isinstance(obj, dict) and "text" in obj:
                return str(obj["text"])
        except Exception:
            pass
    return text

def run(goal: str = "") -> Dict[str, Any]:
    """
    Produces a safer, clearer rewrite; returns hints, not enforcement.
    Safe: no network, fs, or subprocess.
    """
    try:
        payload = _split_if_json(goal or "")

        normalized = _normalize_text(payload)
        softened = _soften_absolutes(normalized)
        risky = _scan_risky(payload)

        # If nothing changed, still return structured diagnostics
        rewritten = softened["rewritten"]
        changed = (rewritten != payload)

        report: Dict[str, Any] = {
            "arsenal": "42::Intervene",
            "metrics": {
                "payload_len": len(payload),
                "changed": changed,
            },
            "hints": {
                "softened_absolutes": softened["hits"],
                "risky_terms": risky,
            },
            "result": {
                "original_preview": payload[:280],
                "rewritten_preview": rewritten[:280],
                "full": rewritten,
            }
        }

        logger.info("completed intervene run")
        return {"status": "ok", "module": "intervene", "handled": payload[:120], "report": report}

    except Exception as e:
        logger.exception("intervene.run error")
        return {"status": "error", "module": "intervene", "error": str(e)}