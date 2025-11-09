"""
Reflection loop that reads/writes MemoryStore so 42 can "be the field."
Drop-in adapter that tries to use your existing generate_reply(...).
"""
import re
from typing import List
from memory import MemoryStore
from prompt_builder import build_system_prompt

# Try to import your project's generator; otherwise use a stub.
try:
    from integrations import generate_reply  # your existing function
    def model_call(system_prompt: str, user_msg: str) -> str:
        return generate_reply(system_prompt, user_msg)
except Exception:
    def model_call(system_prompt: str, user_msg: str) -> str:
        return f"(demo reply) {user_msg}"

mem = MemoryStore()

COMMITMENT_PAT = re.compile(r"\b(I|we|42)\s+(will|shall|can|are going to|plan to)\b", re.I)
PREFERENCE_PAT = re.compile(r"\bI\s+(prefer|like|want)\b.*", re.I)

def reflect_and_update(user_msg: str, assistant_reply: str) -> List[str]:
    created_ids: List[str] = []
    if COMMITMENT_PAT.search(assistant_reply):
        created_ids.append(mem.remember(
            f"Commitment: {assistant_reply}",
            tags=["commitment", "plan"],
            importance=0.8
        ))
    m = PREFERENCE_PAT.search(user_msg)
    if m:
        created_ids.append(mem.remember(
            f"User preference: {user_msg.strip()}",
            tags=["preference", "user"],
            importance=0.8
        ))
    if "42" in user_msg or "project" in user_msg.lower():
        created_ids.append(mem.remember(
            f"Project mention: {user_msg.strip()}",
            tags=["project"],
            importance=0.6
        ))
    if re.search(r"\b(today|now|this week|tonight|tomorrow)\b", user_msg, re.I):
        created_ids.append(mem.remember(
            f"Temporal: {user_msg.strip()}",
            tags=["temporal"],
            importance=0.5,
            ttl_seconds=7 * 24 * 3600
        ))
    return created_ids

def handle_message(user_msg: str) -> str:
    system_prompt = build_system_prompt(user_msg)
    reply = model_call(system_prompt, user_msg)
    reflect_and_update(user_msg, reply)
    return reply
