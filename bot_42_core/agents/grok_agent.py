# bot_42_core/agents/grok_agent.py

import os
import time
from typing import Dict, Any, List

import httpx
from openai import OpenAI

from .agent_core import BaseAgent
from bot_42_core.usage.ledger import record_usage

class GrokAgent(BaseAgent):
    """
    Grok-backed agent using the xAI Grok API.

    Env vars:
      - GROK_API_KEY     (required)
      - GROK_MODEL       (default: "grok-beta")
      - GROK_BASE_URL    (default: "https://api.x.ai/v1")
      - GROK_TIMEOUT     (default: "60")
      - GROK_TEMPERATURE (default: "0.7")
      - GROK_MAX_TOKENS  (default: "2048")
      - GROK_USE_SDK     (default: "true")  # "true"/"false"
    """

    def __init__(self) -> None:
        super().__init__(name="grok", description="Grok (xAI) large language model agent")

        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise ValueError("GROK_API_KEY environment variable is required")

        self.model = os.getenv("GROK_MODEL", "grok-beta")
        self.base_url = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1").rstrip("/")

        self.timeout = float(os.getenv("GROK_TIMEOUT", "60"))
        self.temperature = float(os.getenv("GROK_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("GROK_MAX_TOKENS", "2048"))

        use_sdk_str = os.getenv("GROK_USE_SDK", "true").strip().lower()
        self.use_openai_sdk = use_sdk_str in ("1", "true", "yes", "y", "on")

        # OpenAI-compatible client pointed at xAI base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def run(self, task: str, context: Dict) -> Dict:
        """
        BaseAgent contract: returns dict with agent output + meta.
        """
        print("[GROK] Agent invoked")

        start_time = time.time()

        # Optional: fold context in (kept lightweight)
        # If you want a strict format, you can expand this later.
        user_content = task
        if context:
            user_content = f"{task}\n\nContext:\n{context}"

        messages: List[Dict[str, str]] = [{"role": "user", "content": user_content}]

        try:
            # ---- Option A: OpenAI-compatible SDK (sync call) ----
            if self.use_openai_sdk:
                # The OpenAI client call is sync; run it in a thread so we don't block the event loop.
                import asyncio

                def _sdk_call():
                    return self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )

                resp = await asyncio.to_thread(_sdk_call)

                content = (resp.choices[0].message.content or "").strip()

                # Best-effort usage extraction
                usage = {}
                try:
                    usage = {
                        "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                        "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                        "total_tokens": getattr(resp.usage, "total_tokens", None),
                    }
                except Exception:
                    usage = {}

                return {
                    "agent": self.name,
                    "content": content,
                    "meta": {
                        "provider": "grok",
                        "model": self.model,
                        "mode": "openai_sdk",
                        "timing_s": round(time.time() - start_time, 3),
                        "usage": usage,
                    },
                }

            # ---- Option B: Raw HTTP fallback (async) ----
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()

            content = (data["choices"][0]["message"]["content"] or "").strip()

            return {
                "agent": self.name,
                "content": content,
                "meta": {
                    "provider": "grok",
                    "model": self.model,
                    "mode": "raw_http",
                    "timing_s": round(time.time() - start_time, 3),
                    "usage": data.get("usage", {}),
                },
            }

        except Exception as e:
            # Never crash the whole app because Grok hiccupped
            return {
                "agent": self.name,
                "content": "",
                "error": str(e),
                "meta": {
                    "provider": "grok",
                    "model": self.model,
                    "timing_s": round(time.time() - start_time, 3),
                },
            }