from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from pathlib import Path
from typing import List, Any
import json

# Router instead of a standalone FastAPI app
oracle_router = APIRouter(
    prefix="/oracle",
    tags=["oracle"],
)

# --- Log locations (adjust paths later if you want) ---
LOG_DIR = Path(".")

PROPHECY_LOG = LOG_DIR / "prophecy.log"
REFLECTION_LOG = LOG_DIR / "reflection_log.json"
MEMORY_LOG = LOG_DIR / "memory_log.json"


# ---------- Oracle endpoints ----------

@oracle_router.get("/health", response_class=PlainTextResponse)
def oracle_health() -> str:
    """Lightweight healthcheck for the oracle subsystem."""
    return "ok"


@oracle_router.get("/", response_class=PlainTextResponse)
def get_oracle() -> str:
    """Placeholder oracle response (we’ll hook this into 42 later)."""
    return "This would be a prophecy."


@oracle_router.get("/logs/prophecy", response_class=JSONResponse)
def get_prophecy_log(n: int = Query(10, ge=1, le=200)) -> Any:
    """Return the last N lines from the prophecy log (plain text)."""
    return read_log_lines(PROPHECY_LOG, n)


@oracle_router.get("/logs/reflection", response_class=JSONResponse)
def get_reflection_log(n: int = Query(10, ge=1, le=200)) -> Any:
    """Return the last N entries from the reflection JSON log."""
    return read_json_log(REFLECTION_LOG, n)


@oracle_router.get("/logs/memory", response_class=JSONResponse)
def get_memory_log(n: int = Query(10, ge=1, le=200)) -> Any:
    """Return the last N entries from the memory JSON log."""
    return read_json_log(MEMORY_LOG, n)


@oracle_router.get("/ui", response_class=FileResponse)
def serve_ui() -> FileResponse:
    """
    Serve a simple oracle UI page (index.html) if present.
    Mounted at /oracle/ui so it doesn't clash with the main root.
    """
    return FileResponse("index.html")


# ---------- Helpers ----------

def read_log_lines(path: Path, n: int) -> List[str]:
    """Read the last N lines from a plain text log file."""
    if not path.exists():
        return []
    with open(path, "r") as file:
        return file.readlines()[-n:]


def read_json_log(path: Path, n: int) -> Any:
    """Read the last N items from a JSON log file (list-like)."""
    if not path.exists():
        return []
    with open(path, "r") as file:
        data = json.load(file)
    # If it's a list, return last n items; otherwise just return as-is
    if isinstance(data, list):
        return data[-n:]
    return data