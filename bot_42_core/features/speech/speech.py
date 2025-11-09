# bot_42_core/features/speech/speech.py
from __future__ import annotations

"""
Speech utilities and routes for Bot 42.

Provides:
    GET /speak/logs       → list recorded speech files with metadata
    GET /speak/play/{id}  → stream or download a single speech file
"""

# built-ins
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional
import mimetypes

# fastapi
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

# local imports
from .. import storage_manager


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

# Speech log directory (<BASE_DIR>/logs/speech)
SPEECH_DIR: Path = storage_manager.BASE_DIR / "logs" / "speech"
SPEECH_DIR.mkdir(parents=True, exist_ok=True)

# Recognized audio formats
AUDIO_EXTS: Tuple[str, ...] = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac")

# Router
router = APIRouter(prefix="/speak", tags=["speech"])


# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------

def _iso_utc(ts: float) -> str:
    """Return a UTC ISO-formatted timestamp."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _collect_speech_entries(
    root: Path = SPEECH_DIR,
    limit: int = 50,
    include_hidden: bool = False,
) -> List[Dict[str, object]]:
    """
    Scan `root` for audio files (newest first) and return lightweight metadata.
    """
    if not root.exists():
        return []

    files = [
        p for p in root.rglob("*")
        if p.is_file()
        and (include_hidden or not p.name.startswith("."))
        and p.suffix.lower() in AUDIO_EXTS
    ]

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    entries: List[Dict[str, object]] = []
    for p in files[: max(1, min(limit, 500))]:
        st = p.stat()
        created = getattr(st, "st_ctime", st.st_mtime)
        mime, _ = mimetypes.guess_type(p.name)
        entries.append(
            {
                "id": p.stem,
                "name": p.name,
                "path": str(p.resolve()),
                "mime": mime or "application/octet-stream",
                "size": int(st.st_size),
                "created_utc": _iso_utc(created),
                "modified_utc": _iso_utc(st.st_mtime),
            }
        )
    return entries


def _find_by_id(entry_id: str, root: Path = SPEECH_DIR) -> Optional[Path]:
    """
    Find the newest file whose stem matches `entry_id`.
    """
    candidates = []
    for ext in AUDIO_EXTS:
        candidates.extend(root.rglob(f"{entry_id}{ext}"))

    if not candidates:
        # If caller passed full file name with extension
        candidates = list(root.rglob(entry_id))

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@router.get("/logs")
def list_speech_logs(
    limit: int = Query(50, ge=1, le=500, description="Max number of items to return (newest first)"),
) -> List[Dict[str, object]]:
    """Return newest-first audio metadata from SPEECH_DIR."""
    try:
        return _collect_speech_entries(SPEECH_DIR, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list speech logs: {e}") from e


@router.get("/play/{entry_id}")
def play_speech_by_id(entry_id: str):
    """Stream a single audio file by its stem (file name without extension)."""
    target = _find_by_id(entry_id, SPEECH_DIR)
    if target is None:
        raise HTTPException(status_code=404, detail=f"No speech entry found for id '{entry_id}'")

    mime, _ = mimetypes.guess_type(target.name)
    return FileResponse(
        path=str(target.resolve()),
        media_type=mime or "application/octet-stream",
        filename=target.name,
    )