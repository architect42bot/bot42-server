# bot_42_core/prompt_builder.py
from __future__ import annotations

import os
from typing import Any, Optional


# --- Optional memory support (never crash boot if memory isn't wired yet) ---
_MEM = None
_MEM_ERR: Optional[str] = None

try:
    # Your screenshot shows: from memory import MemoryStore
    from memory import MemoryStore # type: ignore

    # MemoryStore in your stacktrace REQUIRES base_dir
    _default_dir = os.getenv("MEMORY_DIR", "./data/memory")
    os.makedirs(_default_dir, exist_ok=True)

    _MEM = MemoryStore(base_dir=_default_dir) # <-- critical fix
except Exception as e:
    _MEM_ERR = f"{type(e).__name__}: {e}"
    _MEM = None


def build_system_prompt(
    user_msg: str,
    tone: str = "balanced",
    nina: Any = None,
    ethics: Any = None,
    k: int = 8,
) -> str:
    """
    Builds a system prompt for 42.

    - Never crashes if memory isn't available.
    - Pulls top-k memories if MemoryStore is wired.
    - Accepts optional nina/ethics objects (you can expand later).
    """
    memories_block = "(memory disabled)"
    if _MEM is not None:
        try:
            memories = _MEM.recall(user_msg, k=k) or []
            memories_block = "\n".join(f"- {m.get('text', str(m))}" for m in memories) or "(no memory)"
        except Exception as e:
            memories_block = f"(memory recall failed: {type(e).__name__}: {e})"
    else:
        if _MEM_ERR:
            memories_block = f"(memory init failed: {_MEM_ERR})"

    nina_line = ""
    if nina is not None:
        nina_line = "\nNINA: present (state available)."
    else:
        nina_line = "\nNINA: not present."

    ethics_line = ""
    if ethics is not None:
        ethics_line = "\nEthics: present."
    else:
        ethics_line = "\nEthics: not present."

    return f"""You are 42.

Tone: {tone}.{nina_line}{ethics_line}

Relevant memory:
{memories_block}

Rules:
- Be clear and helpful.
- If the user says "status", respond with a short system/health style response.
- If the user says "help", explain briefly what they can ask.

User: {user_msg}
"""