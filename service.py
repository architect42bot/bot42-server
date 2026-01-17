from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse
from bot_42_core.core.protection_infra import protected_dependency


# -----------------------------------------------------------------------------
# Storage locations (simple + reliable)
# -----------------------------------------------------------------------------
BASE_DIR = Path(os.getenv("BOT42_DATA_DIR", "data"))
VOICE_DIR = BASE_DIR / "voice"
VOICE_DIR.mkdir(parents=True, exist_ok=True)

VOICE_LOG_PATH = VOICE_DIR / "voice_log.jsonl"
VOICE_WAV_DIR = VOICE_DIR / "wav"
VOICE_WAV_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Router: SAFE-KEY protected for ALL voice routes (no per-endpoint key params)
# -----------------------------------------------------------------------------
router = APIRouter(
    prefix="/voice",
    tags=["voice"],
    dependencies=[Depends(protected_dependency)],
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip malformed line rather than crashing the API
                continue
    return out


def _latest_entries(limit: int = 10) -> List[Dict[str, Any]]:
    entries = _read_jsonl(VOICE_LOG_PATH)
    if not entries:
        return []
    limit = max(1, min(int(limit), 100))
    return list(reversed(entries))[:limit]


def _get_wav_path(entry: Dict[str, Any]) -> Optional[Path]:
    # Common keys you might store
    wav_name = entry.get("wav") or entry.get("filename") or entry.get("file") or entry.get("wav_file")
    if not wav_name:
        return None
    p = Path(wav_name)
    # If it's already absolute, use it. If not, assume it lives in VOICE_WAV_DIR.
    return p if p.is_absolute() else (VOICE_WAV_DIR / p.name)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.get("/health")
async def voice_health() -> Dict[str, Any]:
    """
    Health check for the voice subsystem.
    Confirms routing + auth + module load.
    """
    return {
        "voice_ready": True,
        "log_path": str(VOICE_LOG_PATH),
        "wav_dir": str(VOICE_WAV_DIR),
        "notes": "ok",
    }


@router.get("/last")
async def voice_last() -> Dict[str, Any]:
    entries = _latest_entries(limit=1)
    last = entries[0] if entries else None
    return {"status": "ok", "last": last}


@router.get("/last/play_legacy")
async def voice_last_play() -> FileResponse:
    entries = _latest_entries(limit=1)
    if not entries:
        raise HTTPException(status_code=404, detail="No voice entries available.")
    wav_path = _get_wav_path(entries[0])
    if not wav_path or not wav_path.exists():
        raise HTTPException(status_code=404, detail="Last entry has no playable wav file.")
    return FileResponse(str(wav_path), media_type="audio/wav", filename=wav_path.name)


@router.get("/last/play")
async def voice_last_play_alias():
    return RedirectResponse(
        url="/api/voice/last/play",
        status_code=307
    )

@router.get("/recent")
async def voice_recent(limit: int = Query(10, ge=1, le=100)) -> Dict[str, Any]:
    items = _latest_entries(limit=limit)
    return {"status": "ok", "count": len(items), "items": items}


@router.get("/find")
async def voice_find(q: str = Query(..., min_length=1), limit: int = Query(25, ge=1, le=100)) -> Dict[str, Any]:
    q_lower = q.lower().strip()
    entries = _read_jsonl(VOICE_LOG_PATH)
    hits: List[Dict[str, Any]] = []
    for e in reversed(entries):
        blob = json.dumps(e, ensure_ascii=False).lower()
        if q_lower in blob:
            hits.append(e)
            if len(hits) >= limit:
                break
    return {"status": "ok", "q": q, "count": len(hits), "items": hits}