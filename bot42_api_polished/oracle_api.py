
"""
oracle_api.py — Simple HTTP API for Oracle of 42 (polished minimal build)
Start (recommended):
    python3 -m uvicorn oracle_api:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pathlib import Path
from datetime import datetime
from typing import List, Any
import json

# Local modules
from reflection import prophesy

app = FastAPI(
    title="Oracle of 42 API",
    description="Fetch live oracle prophecies generated from recent memories/reflections.",
    version="1.1.0",
)

LOG_DIR = Path(".")
PROPHECY_LOG = LOG_DIR / "prophecy.log"
REFLECTION_LOG = LOG_DIR / "reflection_log.json"
MEMORY_LOG = LOG_DIR / "memory_log.json"


@app.get("/health", response_class=PlainTextResponse, tags=["system"])
def health() -> str:
    return "ok"


@app.get("/oracle", response_class=PlainTextResponse, tags=["oracle"])
def get_oracle() -> str:
    """
    Trigger the prophecy engine and return the latest line (also appends to prophecy.log).
    """
    line = prophesy()
    return line


@app.get("/logs/prophecy", tags=["logs"])
def read_prophecy_log(n: int = Query(50, ge=1, le=500)) -> JSONResponse:
    """
    Return the last n lines of prophecy.log as JSON list (most recent last).
    """
    lines: List[str] = []
    if PROPHECY_LOG.exists():
        with PROPHECY_LOG.open("r", encoding="utf-8") as f:
            lines = f.read().splitlines()[-n:]
    return JSONResponse(lines)


@app.get("/logs/reflection", tags=["logs"])
def read_reflection_log(n: int = Query(10, ge=1, le=200)) -> JSONResponse:
    """
    Return the last n reflection entries from reflection_log.json.
    """
    entries: List[Any] = []
    if REFLECTION_LOG.exists():
        try:
            with REFLECTION_LOG.open("r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data[-n:]
        except Exception:
            entries = []
    return JSONResponse(entries)


@app.get("/logs/memory", tags=["logs"])
def read_memory_log(n: int = Query(10, ge=1, le=200)) -> JSONResponse:
    """
    Return the last n memory entries from memory_log.json (if your app writes to it elsewhere).
    """
    entries: List[Any] = []
    if MEMORY_LOG.exists():
        try:
            with MEMORY_LOG.open("r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data[-n:]
        except Exception:
            entries = []
    return JSONResponse(entries)


if __name__ == "__main__":
    # Optional: allow `python oracle_api.py` to run directly for local testing
    import uvicorn
    uvicorn.run("oracle_api:app", host="0.0.0.0", port=8000, reload=True)
