# bot_42_core/features/dispatcher.py

def dispatch(text: str) -> dict:
    """
    Minimal rule-based router. Expand later.
    Returns a dict so callers can log/inspect.
    """
    t = (text or "").lower().strip()

    if any(k in t for k in ("law", "policy", "regulation", "statute")):
        return {"route": "law", "text": text}
    if any(k in t for k in ("intervene", "act on", "do this", "execute")):
        return {"route": "intervene", "text": text}
    if any(k in t for k in ("infiltrate", "probe", "scan", "inspect")):
        return {"route": "infiltrate", "text": text}

    return {"route": "none", "text": text}