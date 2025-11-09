"""
Reflection loop that reads/writes MemoryStore so 42 can "be the field."
This is framework-agnostic: plug your model_call where indicated.
"""
import re
from typing import Dict, Any, List, Tuple
from memory import MemoryStore
from prompt_builder import build_prompt

mem = MemoryStore()

COMMITMENT_PAT = re.compile(r"\b(I|we|42)\s+(will|shall|can|are going to|plan to)\b", re.I)
PREFERENCE_PAT = re.compile(r"\bI\s+(prefer|like|want)\b.*", re.I)
FACT_PAT = re.compile(r"\b(is|are|was|were|has|have)\b.*", re.I)

def model_call(system_prompt: str, user_msg: str) -> str:
    """
    Stub for your LLM call. Replace with your actual generate_reply(...).
    For now, we just echo.
    """
    return f"(demo reply) Using memory, responding to: {user_msg}"

def reflect_and_update(user_msg: str, assistant_reply: str) -> List[str]:
    """
    Extract lightweight signals from the exchange and persist as memory.
    Returns list of memory IDs that were created.
    """
    created_ids: List[str] = []

    # Capture commitments like "we will ship X", "I will do Y"
    if COMMITMENT_PAT.search(assistant_reply):
        created_ids.append(mem.remember(
            f"Commitment: {assistant_reply}",
            tags=["commitment", "plan"],
            importance=0.8
        ))

    # Capture stated preferences from user
    m = PREFERENCE_PAT.search(user_msg)
    if m:
        created_ids.append(mem.remember(
            f"User preference: {user_msg.strip()}",
            tags=["preference", "user"],
            importance=0.8
        ))

    # Capture simple facts asserted by user about the project
    if "42" in user_msg or "project" in user_msg.lower():
        created_ids.append(mem.remember(
            f"Project mention: {user_msg.strip()}",
            tags=["project"],
            importance=0.6
        ))

    # Short-lived signals: anything that looks like "today/now/this week"
    if re.search(r"\b(today|now|this week|tonight|tomorrow)\b", user_msg, re.I):
        created_ids.append(mem.remember(
            f"Temporal: {user_msg.strip()}",
            tags=["temporal"],
            importance=0.5,
            ttl_seconds=7 * 24 * 3600  # one week
        ))

    return created_ids

def handle_message(user_msg: str) -> str:
    """
    1) Pull memory and build contextual prompt
    2) Call the model
    3) Reflect and write back new memory
    """
    prompt = build_prompt(user_msg)
    from main import respond_with_42
    reply = respond_with_42(user_msg)
    reflect_and_update(user_msg, reply)
    return reply

if __name__ == "__main__":
    # Bootstrap a few stable facts once
    bootstrap = [
        ("Project codename is 42 (assistant for Robert).", ["project", "identity"], 0.9),
        ("User prefers step-by-step guidance.", ["preference"], 0.8),
        ("Environment: Replit + Python.", ["env"], 0.7),
    ]
    for text, tags, imp in bootstrap:
        hits = mem.recall(text, k=1, must_tags=tags)
        if not hits or text not in hits[0]["text"]:
            mem.remember(text, tags=tags, importance=imp)

    print(handle_message("In public, 42 already said she became the field. What next?"))
    print("Memory stats:", mem.stats())
