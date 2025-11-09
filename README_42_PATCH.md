# 42 Repo Patch — Memory + Reflection Loop

This patch drops a memory-backed reflection loop into your repo without changing your existing model code.

## Files (place in `bot_42_core/` or your app root)

- `memory.py` — persistent JSON memory store
- `prompt_builder.py` — pulls top memories and builds the system prompt
- `reflection_loop.py` — calls your model, then writes back new memories
- `main.py` — optional entry to test locally

> By default, `reflection_loop.py` tries to import `generate_reply` from `integrations.py`.  
> If it can't, it uses a demo stub so nothing breaks.

## Quick Start (Replit)

1. Upload & unzip the patch.
2. In the Shell:
   ```bash
   python3 main.py
   ```
3. You should see Before/After memory stats and a new `memory_store.json` created.

## Wiring into your app

**If you already call your model directly**, replace that call with:

```python
from reflection_loop import handle_message

reply = handle_message(user_text)
```

**If your generator is different from `integrations.generate_reply`**, open `reflection_loop.py` and change:

```python
from integrations import generate_reply
def model_call(system_prompt: str, user_msg: str) -> str:
    return generate_reply(system_prompt, user_msg)
```

to match your function signature.

## Optional: Auto-bootstrap facts

At startup (once), seed facts like project identity and prefs:

```python
from memory import MemoryStore
mem = MemoryStore()
mem.remember("Project codename is 42 (assistant for Robert).", tags=["project","identity"], importance=0.9)
mem.remember("User prefers step-by-step guidance.", tags=["preference"], importance=0.8)
```

## Notes

- No external packages. Safe, atomic writes via `.tmp` swap.
- Use tags/importance/TTL to shape retrieval.
- Run `mem.prune_expired()` occasionally.
