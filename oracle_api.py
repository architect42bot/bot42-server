# oracle_api.py

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from pathlib import Path
from datetime import datetime
from typing import List, Any
import json

# This directory is where logs live (adjust if needed)
LOG_DIR = Path(".")
PROPHECY_LOG = LOG_DIR / "prophecy.log"
REFLECTION_LOG = LOG_DIR / "reflection_log.json"
MEMORY_LOG = LOG_DIR / "memory_log.json"

# Router instead of a full FastAPI app
oracle_router = APIRouter(
    prefix="/oracle",
    tags=["oracle"],
)


@oracle_router.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@oracle_router.get("/", response_class=PlainTextResponse)
def get_oracle() -> str:
    # Placeholder — we’ll wire this to 42’s gnostic oracle voice later
    return "This would be a prophecy."


@oracle_router.get("/logs/prophecy", response_class=JSONResponse)
def get_prophecy_log(n: int = 10) -> Any:
    return read_log_lines(PROPHECY_LOG, n)


@oracle_router.get("/logs/reflection", response_class=JSONResponse)
def get_reflection_log(n: int = 10) -> Any:
    return read_json_log(REFLECTION_LOG, n)


@oracle_router.get("/logs/memory", response_class=JSONResponse)
def get_memory_log(n: int = 10) -> Any:
    return read_json_log(MEMORY_LOG, n)


# --- Helpers ----------------------------------------------------------


def read_log_lines(path: Path, n: int) -> List[str]:
    if not path.exists():
        return []
    with open(path, "r") as file:
        return file.readlines()[-n:]


def read_json_log(path: Path, n: int) -> Any:
    if not path.exists():
        return []
    with open(path, "r") as file:
        data = json.load(file)
    # assume list-like JSON log
    return data[-n:]