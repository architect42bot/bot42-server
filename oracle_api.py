
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
from pathlib import Path
from datetime import datetime
from typing import List, Any
import json

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
    return "This would be a prophecy."

@app.get("/logs/prophecy", response_class=JSONResponse, tags=["logs"])
def get_prophecy_log(n: int = 10) -> Any:
    return read_log_lines(PROPHECY_LOG, n)

@app.get("/logs/reflection", response_class=JSONResponse, tags=["logs"])
def get_reflection_log(n: int = 10) -> Any:
    return read_json_log(REFLECTION_LOG, n)

@app.get("/logs/memory", response_class=JSONResponse, tags=["logs"])
def get_memory_log(n: int = 10) -> Any:
    return read_json_log(MEMORY_LOG, n)

@app.get("/", response_class=FileResponse)
def serve_ui():
    return FileResponse("index.html")

def read_log_lines(path: Path, n: int) -> List[str]:
    if not path.exists():
        return []
    with open(path, "r") as file:
        return file.readlines()[-n:]

def read_json_log(path: Path, n: int) -> Any:
    if not path.exists():
        return []
    with open(path, "r") as file:
        return json.load(file)[-n:]
