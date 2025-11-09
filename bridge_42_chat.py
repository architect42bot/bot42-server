# bridge_42_chat.py
"""
Simple bridge so external tools can talk to 42's Christ-ethics
microservice running on http://127.0.0.1:8000.
"""

from typing import Dict, Any
import requests

API_URL = "http://127.0.0.1:8000/chat"


def run(text: str, mode: str = "christlike") -> Dict[str, Any]:
    """
    Send a message to 42's /chat endpoint and return the JSON reply.
    """
    payload = {"input": text, "mode": mode}

    resp = requests.post(API_URL, json=payload, timeout=15)
    resp.raise_for_status()

    return resp.json()
