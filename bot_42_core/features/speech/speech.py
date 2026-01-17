# bot_42_core/features/speech/speech.py
from __future__ import annotations

import asyncio
import io
import mimetypes
import os
import re
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse

from .. import storage_manager
import json
# Configuration
SPEECH_DIR: Path = storage_manager.BASE_DIR / "logs" / "speech"
SPEECH_DIR.mkdir(parents=True, exist_ok=True)

SPEECH_LOG_PATH = SPEECH_DIR / "speech_log.jsonl"


def _append_speech_log(rec: dict) -> None:
    """
    Append one JSON line to the speech log.
    Never raises (logging must not break synthesis).
    """
    try:
        SPEECH_DIR.mkdir(parents=True, exist_ok=True)
        rec = dict(rec)
        rec.setdefault("ts", datetime.utcnow().isoformat())
        with open(SPEECH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

# Speech log directory (<BASE_DIR>/logs/speech)
SPEECH_DIR: Path = storage_manager.BASE_DIR / "logs" / "speech"
SPEECH_DIR.mkdir(parents=True, exist_ok=True)
SPEECH_LOG_PATH = SPEECH_DIR / "speech_log.jsonl"

# Recognized formats (primarily for listing / future expansion)
AUDIO_EXTS: Tuple[str, ...] = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".aac")

# Default voice/rate (override via env)
DEFAULT_VOICE: str = (os.getenv("BOT42_TTS_VOICE", "en-GB-LibbyNeural") or "en-GB-LibbyNeural").strip()
DEFAULT_RATE: str = (os.getenv("BOT42_TTS_RATE", "+0%") or "+0%").strip()

# If edge-tts returns very tiny files, they tend to be silence/invalid
MIN_WAV_BYTES = 2000

# Canonical speech synthesis endpoints live under /speak/*
# /voice/* is reserved for health/readiness and voice metadata (no synthesis)
router = APIRouter(prefix="/speak", tags=["speech"])

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{3,80}$")


def _validate_speech_id(speech_id: str) -> str:
    speech_id = (speech_id or "").strip()
    if not speech_id:
        raise HTTPException(status_code=400, detail="Missing speech id.")
    if not _ID_RE.match(speech_id):
        raise HTTPException(status_code=400, detail="Invalid speech id.")
    if ".." in speech_id or "/" in speech_id or "\\" in speech_id:
        raise HTTPException(status_code=400, detail="Invalid speech id.")
    return speech_id


def _resolve_wav_path(speech_dir: Path, speech_id: str) -> Path:
    speech_id = _validate_speech_id(speech_id)
    p = (speech_dir / f"{speech_id}.wav").resolve()
    base = speech_dir.resolve()
    if base not in p.parents:
        raise HTTPException(status_code=400, detail="Invalid path.")
    if not p.exists():
        raise HTTPException(status_code=404, detail="Speech file not found.")
    return p


def _iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _silence_wav_bytes(duration_s: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a valid WAV file containing silence."""
    n_channels = 1
    sampwidth = 2  # 16-bit PCM
    n_frames = int(duration_s * sample_rate)
    silence = b"\x00\x00" * n_frames

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(silence)
    return buf.getvalue()


def _collect_speech_entries(
    root: Path = SPEECH_DIR,
    limit: int = 50,
    include_hidden: bool = False,
) -> List[Dict[str, object]]:
    """
    Scan root for .wav files (newest first) and return metadata entries.
    """
    root = root.resolve()
    if not root.exists():
        return []

    files = []
    for p in root.glob("*.wav"):
        name = p.name
        if (not include_hidden) and name.startswith("."):
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        files.append((p, st.st_mtime, st.st_size))

    files.sort(key=lambda x: x[1], reverse=True)
    out: List[Dict[str, object]] = []

    for p, mtime, size in files[: max(1, limit)]:
        speech_id = p.stem  # "say_2025..." etc.
        out.append(
            {
                "id": speech_id,
                "file": p.name,
                "size_bytes": size,
                "modified_utc": _iso_utc(mtime),
                "mime": mimetypes.guess_type(p.name)[0] or "audio/wav",
                "kind": "say" if speech_id.startswith("say_") else "test" if speech_id.startswith("test_") else "speech",
            }
        )
    return out


async def _edge_tts_to_wav_bytes(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
) -> bytes:
    """
    Uses edge-tts to synthesize speech to a WAV file, then returns WAV bytes.
    """
    # Local import so module doesn't hard-crash if dependency missing
    import edge_tts

    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text'.")

    voice = (voice or DEFAULT_VOICE).strip() or DEFAULT_VOICE
    rate = (rate or DEFAULT_RATE).strip() or DEFAULT_RATE

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            data = f.read()

        return data
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def tts_wav_bytes(text: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> bytes:
    """
    Sync wrapper for TTS (routes are sync in your project right now).
    """
    try:
        return asyncio.run(_edge_tts_to_wav_bytes(text=text, voice=voice, rate=rate))
    except RuntimeError:
        # if an event loop already exists
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_edge_tts_to_wav_bytes(text=text, voice=voice, rate=rate))
        finally:
            loop.close()


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@router.get("/logs")
def speak_logs(
    limit: int = Query(50, ge=1, le=500),
    include_hidden: bool = Query(False),
):
    return {
        "ok": True,
        "dir": str(SPEECH_DIR),
        "default_voice": DEFAULT_VOICE,
        "default_rate": DEFAULT_RATE,
        "items": _collect_speech_entries(SPEECH_DIR, limit=limit, include_hidden=include_hidden),
    }


@router.get("/last")
def speak_last():
    items = _collect_speech_entries(SPEECH_DIR, limit=1, include_hidden=False)
    if not items:
        return {"ok": True, "item": None}
    return {"ok": True, "item": items[0]}


@router.get("/test")
def speech_test():
    """
    Simple speech test - creates a valid silent .wav file in SPEECH_DIR
    so that /speak/logs and /speak/last have something to show.
    """
    SPEECH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    file_path = SPEECH_DIR / f"test_{ts}.wav"
    speech_id = file_path.stem
    file_path.write_bytes(_silence_wav_bytes(duration_s=1.0, sample_rate=16000))
    return {"ok": True, "file": file_path.name, "id": file_path.stem}

# Canonical speech synthesis endpoints live under /speak/*
# /voice/* is reserved for health, readiness, and system metadata
@router.post("/say")
def speak_say(payload: dict = Body(...)):
    """
    Generate REAL speech via edge-tts, save a wav in SPEECH_DIR, return the filename.

    Body example:
      { "text": "Hello world", "voice": "en-GB-LibbyNeural", "rate": "+0%" }
    """
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Missing 'text'")

    # If caller omits voice/rate, we use defaults (Libby + DEFAULT_RATE)
    voice = (payload.get("voice") or DEFAULT_VOICE).strip() or DEFAULT_VOICE
    rate = (payload.get("rate") or DEFAULT_RATE).strip() or DEFAULT_RATE

    SPEECH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    file_path = SPEECH_DIR / f"say_{ts}.wav"
    speech_id = file_path.stem

    wav_bytes = tts_wav_bytes(text=text, voice=voice, rate=rate)

    # Sanity check: prevents creating "nothing to play" junk
    if not wav_bytes or len(wav_bytes) < MIN_WAV_BYTES:
        raise HTTPException(status_code=500, detail="TTS returned empty/too-small audio")

    file_path.write_bytes(wav_bytes)
    _append_speech_log({
        "kind": "say",
        "id": speech_id,
        "file": file_path.name,
        "path": str(file_path),
        "voice": voice,
        "rate": rate,
        "bytes": len(wav_bytes),
    })
    
    return {"ok": True, "file": file_path.name, "id": file_path.stem, "voice": voice, "rate": rate}


@router.get("/play/{speech_id}")
def speak_play(speech_id: str):
    """
    Stream/download a speech WAV by id (stem, without .wav).
    Example: /speak/play/say_20251221T202152
    """
    p = _resolve_wav_path(SPEECH_DIR, speech_id)

    # Force correct type
    media_type = "audio/wav"

    return FileResponse(
        path=str(p),
        media_type=media_type,
        filename=p.name,
    )

def save_tts_wav(text: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> str:
    """
    Generate a WAV using TTS and save to SPEECH_DIR.
    Returns speech_id (stem) e.g. 'say_20251221T202152'
    """
    SPEECH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    speech_id = f"say_{ts}"
    file_path = SPEECH_DIR / f"{speech_id}.wav"

    wav_bytes = tts_wav_bytes(text=text, voice=voice, rate=rate)
    if not wav_bytes or len(wav_bytes) < MIN_WAV_BYTES:
        raise HTTPException(status_code=500, detail="TTS returned empty/too-small audio")

    file_path.write_bytes(wav_bytes)
    return speech_id
