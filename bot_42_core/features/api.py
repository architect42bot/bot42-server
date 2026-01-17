# bot_42_core/features/api.py

from __future__ import annotations

import os
import wave
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from bot_42_core.features.speech import speech as speech_module

router = APIRouter()

# ---------------------------------------------------------------------
# Internal helpers (reusable)
# ---------------------------------------------------------------------


def _wav_duration_ms(path: Path) -> Optional[int]:
    """Return duration in ms if readable; otherwise None."""
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if not rate:
                return None
            return int((frames / rate) * 1000)
    except Exception:
        return None


def _latest_say_entry(limit: int = 50) -> Optional[Dict[str, Any]]:
    """Return newest entry where kind == 'say', or None."""
    entries = speech_module._collect_speech_entries(limit=limit)
    say_entries = [e for e in entries if e.get("kind") == "say"]
    if not say_entries:
        return None

    say_entries.sort(key=lambda e: e.get("modified_utc", ""), reverse=True)
    return say_entries[0]


def get_last_voice_meta(limit: int = 50) -> Optional[Dict[str, Any]]:
    """
    Safe helper for chat pipeline.
    Returns metadata dict or None if unavailable.
    """
    last = _latest_say_entry(limit=limit)
    if not last:
        return None

    filename = str(last.get("file", "")).strip()
    if not filename:
        return None

    file_path = Path(speech_module.SPEECH_DIR) / filename
    if not file_path.exists():
        return None

    size_bytes = last.get("size_bytes")
    if size_bytes is None:
        try:
            size_bytes = os.path.getsize(file_path)
        except Exception:
            size_bytes = None

    duration_ms = _wav_duration_ms(file_path)
    if duration_ms is None and isinstance(size_bytes, int) and size_bytes > 0:
        # Fallback heuristic (~32KB/sec WAV) → ms
        duration_ms = int((size_bytes / 32000) * 1000)

    return {
        "ok": True,
        "id": last.get("id"),
        "file": last.get("file"),
        "mime": last.get("mime", "audio/wav"),
        "modified_utc": last.get("modified_utc"),
        "size_bytes": size_bytes,
        "duration_ms": duration_ms,
        "play_url": "/api/voice/last/play",
    }


def _require_last_voice_file(limit: int = 50) -> tuple[Dict[str, Any], Path]:
    """Raise HTTPException if last voice or file missing; otherwise return (entry, path)."""
    last = _latest_say_entry(limit=limit)
    if not last:
        raise HTTPException(status_code=404, detail="No voice entries available.")

    filename = str(last.get("file", "")).strip()
    if not filename:
        raise HTTPException(status_code=404, detail="Last entry has no file.")

    file_path = Path(speech_module.SPEECH_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Last voice file missing on disk.")

    return last, file_path


# ---------------------------------------------------------------------
# Routes: Voice (human-friendly)
# ---------------------------------------------------------------------


@router.get("/voice/health")
def voice_health() -> Dict[str, Any]:
    """Health check for the voice subsystem. Confirms routing + auth + module load."""
    return {
        "voice_ready": True,
        "log_path": str(getattr(speech_module, "SPEECH_LOG_PATH", "")),
        "wav_dir": str(getattr(speech_module, "SPEECH_DIR", "")),
        "notes": "ok",
    }


@router.get("/voice/last")
def voice_last() -> Dict[str, Any]:
    last = _latest_say_entry(limit=1)
    return {"status": "ok", "last": last}


@router.get("/voice/last/meta")
def voice_last_meta() -> Dict[str, Any]:
    meta = get_last_voice_meta(limit=50)
    if not meta:
        raise HTTPException(status_code=404, detail="No voice entries available.")
    return meta


@router.get("/voice/last/play")
def voice_last_play() -> FileResponse:
    last, file_path = _require_last_voice_file(limit=50)
    return FileResponse(
        path=str(file_path),
        media_type=last.get("mime", "audio/wav"),
        filename=file_path.name,
    )


@router.get("/voice/recent")
def voice_recent(
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    entries = speech_module._collect_speech_entries(limit=limit)
    return {"status": "ok", "count": len(entries), "items": entries}


@router.get("/voice/find")
def voice_find(
    q: str = Query(..., min_length=1),
    limit: int = Query(25, ge=1, le=100),
) -> Dict[str, Any]:
    qn = q.lower().strip()
    entries = speech_module._collect_speech_entries(limit=limit)

    hits = [
        e
        for e in entries
        if qn in (e.get("text") or "").lower()
        or qn in (e.get("file") or "").lower()
    ]

    return {"status": "ok", "query": qn, "count": len(hits), "items": hits}


# ---------------------------------------------------------------------
# Routes: API (internal / programmatic)
# ---------------------------------------------------------------------


@router.get("/api/voice/last/meta")
def api_voice_last_meta() -> Dict[str, Any]:
    meta = get_last_voice_meta(limit=50)
    if not meta:
        raise HTTPException(status_code=404, detail="No voice entries available.")
    return meta


@router.get("/api/voice/last/play")
def api_voice_last_play() -> FileResponse:
    last, file_path = _require_last_voice_file(limit=50)
    return FileResponse(
        path=str(file_path),
        media_type=last.get("mime", "audio/wav"),
        filename=file_path.name,
    )