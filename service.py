from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from bot_42_core.core.protection_infra import enforce_safe_api_key

router = APIRouter(prefix="/voice", tags=["voice"])


# --------------------------------------------------------------------
# TEMP STUB DATA (replace with real speech log storage later)
# --------------------------------------------------------------------
def _stub_entries() -> List[Dict[str, Any]]:
    return [
        {"id": "stub-1", "label": "boot", "name": "boot.wav"},
        {"id": "stub-2", "label": "test", "name": "test.wav"},
    ]


def _find_entries(q: str, limit: int) -> List[Dict[str, Any]]:
    q = (q or "").strip().lower()
    if not q:
        return []

    entries = _stub_entries()
    out: List[Dict[str, Any]] = []

    for e in entries:
        hay = f"{e.get('id','')} {e.get('label','')} {e.get('name','')}".lower()
        if q in hay:
            out.append(e)
        if len(out) >= limit:
            break

    return out


# --------------------------------------------------------------------
# ROUTES (SAFE-KEY protected)
# --------------------------------------------------------------------
@router.get("/health")
async def voice_health(_: None = Depends(enforce_safe_api_key)):
    """
    Health check for the voice subsystem.
    Confirms routing + auth + module load.
    """
    return {
        "status": "ok",
        "service": "voice"
    }
@router.get("/last")
async def voice_last(_: None = Depends(enforce_safe_api_key)) -> Dict[str, Any]:
    entries = _stub_entries()
    last = entries[-1] if entries else None
    return {"status": "ok", "last": last}


@router.get("/last/play")
async def voice_last_play(_: None = Depends(enforce_safe_api_key)) -> Dict[str, Any]:
    entries = _stub_entries()
    if not entries:
        raise HTTPException(status_code=404, detail="No voice entries available.")
    last = entries[-1]
    return {"status": "ok", "play": last}


@router.get("/recent")
async def voice_recent(
    limit: int = 10,
    _: None = Depends(enforce_safe_api_key),
) -> Dict[str, Any]:
    limit = max(1, min(int(limit), 100))
    entries = _stub_entries()
    recent = list(reversed(entries))[:limit]
    return {"status": "ok", "count": len(recent), "items": recent}


@router.get("/find")
async def voice_find(
    q: str,
    limit: int = 20,
    _: None = Depends(enforce_safe_api_key),
) -> Dict[str, Any]:
    limit = max(1, min(int(limit), 100))
    results = _find_entries(q=q, limit=limit)
    return {"status": "ok", "query": q, "count": len(results), "items": results}