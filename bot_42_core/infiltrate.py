# infiltrate.py
# 42 :: INFILTRATE (safe context mining & signal extraction)
# Public entrypoint: run(goal: str) -> Dict[str, Any]

from __future__ import annotations

from typing import Dict, Any, List, Tuple
import re
import json
import logging
from collections import Counter

logger = logging.getLogger("infiltrate")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] infiltrate: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ---------- small helpers ----------
WORD = re.compile(r"[A-Za-z0-9_]+")
URL = re.compile(r"(https?://[^\s]+)", re.I)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
NUMBER = re.compile(r"(?<![\w.])(?:-?\d+(?:\.\d+)?)(?![\w.])")

def _top_k(items: List[str], k: int = 10) -> List[Tuple[str, int]]:
    c = Counter(x.lower() for x in items if x and x.strip())
    return c.most_common(k)

def _split_if_json(text: str) -> str:
    """If goal looks like JSON with a 'text' field, pull it out."""
    t = text.strip()
    if t.startswith("{"):
        try:
            obj = json.loads(t)
            if isinstance(obj, dict) and "text" in obj:
                return str(obj["text"])
        except Exception:
            pass
    return text

# ---------- public entrypoint ----------
def run(goal: str = "") -> Dict[str, Any]:
    """
    Extracts signals (urls, emails, numbers, keywords) from the payload.
    Safe: no network, fs, or subprocess.
    """
    try:
        payload = _split_if_json(goal or "")
        tokens = WORD.findall(payload)
        urls = URL.findall(payload)
        emails = EMAIL.findall(payload)
        numbers = NUMBER.findall(payload)

        keywords = [t for t in tokens if len(t) > 3]
        top_keywords = _top_k(keywords, k=12)

        entities_guess = [t for t in tokens if t.istitle() and len(t) > 2]
        top_entities = _top_k(entities_guess, k=12)

        report: Dict[str, Any] = {
            "arsenal": "42::Infiltrate",
            "metrics": {
                "payload_len": len(payload),
                "token_count": len(tokens),
            },
            "signals": {
                "urls": urls,
                "emails": emails,
                "numbers": numbers,
                "top_keywords": [{"text": k, "count": n} for k, n in top_keywords],
                "top_entities": [{"text": k, "count": n} for k, n in top_entities],
            },
            "preview": payload[:280],
        }

        logger.info("completed infiltrate run")
        return {"status": "ok", "module": "infiltrate", "handled": payload[:120], "report": report}

    except Exception as e:
        logger.exception("infiltrate.run error")
        return {"status": "error", "module": "infiltrate", "error": str(e)}