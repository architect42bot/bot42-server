# features/storage_manager.py
from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---- Paths ----
BASE_DIR = Path(__file__).resolve().parent.parent  # project root
STORAGE_DIR = BASE_DIR / "storage"
AUDIO_DIR = STORAGE_DIR / "audio_logs"
INDEX_PATH = STORAGE_DIR / "audio_log_index.json"


def _utc_now_iso() -> str:
    # Use Zulu (UTC) timestamps for consistency
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    """
    Ensure the storage directories (and index file placeholder) exist.
    Safe to call multiple times.
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    # Create index file if missing
    if not INDEX_PATH.exists():
        _atomic_write_json(INDEX_PATH, [])


def _atomic_write_json(path: Path, data: Any) -> None:
    """
    Write JSON atomically to avoid index corruption.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)  # atomic on POSIX
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _load_index() -> List[Dict[str, Any]]:
    if not INDEX_PATH.exists():
        return []
    try:
        with INDEX_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        # If the index is unreadable, don't crash the app
        return []


def _safe_slug(text: str) -> str:
    # Keep filenames simple and portable
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in text)[:60]


def log_audio(
    *,
    text: str,
    source: str,
    audio_bytes: bytes,
    ext: str = "wav",
    duration: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Save an audio file and append a log entry to audio_log_index.json.
    Returns the log entry dict.
    """
    ensure_dirs()

    ts = _utc_now_iso()  # e.g., 2025-11-01T18:36:27.123456+00:00
    ts_for_filename = ts.replace(":", "-")  # avoid ':' in filenames (Windows-safe)
    source_slug = _safe_slug(source or "speak")
    filename = f"{ts_for_filename}_{source_slug}.{ext}"
    filepath = AUDIO_DIR / filename

    # Write audio file
    with filepath.open("wb") as f:
        f.write(audio_bytes)

    # Build entry
    entry: Dict[str, Any] = {
        "timestamp": ts,
        "source": source,
        "text": text,
        "duration": duration,  # seconds (optional)
        "path": str(filepath.relative_to(BASE_DIR)),
    }
    if extra:
        entry["extra"] = extra

    # Update index (prepend newest)
    index = _load_index()
    index.insert(0, entry)
    _atomic_write_json(INDEX_PATH, index)
    return entry


def list_audio_logs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Return recent audio log entries (most recent first).
    """
    index = _load_index()
    start = max(offset, 0)
    end = max(start + limit, 0)
    return index[start:end]