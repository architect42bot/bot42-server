
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
    
import os
import importlib
import pytest
from fastapi.testclient import TestClient


def _import_app():
    """
    Try common module locations until we find a FastAPI 'app'.
    Adjust the candidates if your app lives somewhere else.
    """
    candidates = [
        "main",                 # main.py at repo root (not your case right now)
        "bot_42_core.main",     # bot_42_core/main.py
        "bot_42_core.app",      # bot_42_core/app.py
        "bot_42_core.api",      # bot_42_core/api.py (less common)
    ]

    last_err = None
    for modname in candidates:
        try:
            mod = importlib.import_module(modname)
            app = getattr(mod, "app", None)
            if app is not None:
                return mod, app
        except Exception as e:
            last_err = e

    raise RuntimeError(
        "Could not import FastAPI app. Tried: "
        + ", ".join(candidates)
        + f". Last error: {last_err}"
    )


def _import_speech_module():
    """
    Try common speech module locations so we can patch SPEECH_DIR.
    """
    candidates = [
        "bot_42_core.features.speech.speech",
        "features.speech.speech",
    ]

    last_err = None
    for modname in candidates:
        try:
            return importlib.import_module(modname)
        except Exception as e:
            last_err = e

    raise RuntimeError(
        "Could not import speech module. Tried: "
        + ", ".join(candidates)
        + f". Last error: {last_err}"
    )


@pytest.fixture()
def client_and_headers(tmp_path, monkeypatch):
    # auth header key
    monkeypatch.setenv("SAFE_KEY", "test-key")

    # import app module AFTER env is set
    app_mod, app = _import_app()
    importlib.reload(app_mod)

    client = TestClient(app)

    # Patch the *actual* speech module used by the FastAPI route
    speech_test_route = next(
        r for r in app.routes if getattr(r, "path", None) == "/speak/test"
    )
    speech_modname = speech_test_route.endpoint.__module__

    import importlib
    speech_module = importlib.import_module(speech_modname)

    speech_module.SPEECH_DIR = tmp_path
    tmp_path.mkdir(parents=True, exist_ok=True)

    headers = {"SAFE-KEY": os.environ["SAFE_KEY"]}
    return client, headers, tmp_path