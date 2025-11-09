from memory import MemoryStore

mem = MemoryStore()

def build_system_prompt(user_msg: str) -> str:
    """
    Builds a system/context prompt for 42 using top-k persistent memories.
    """
    memories = mem.recall(user_msg, k=8)
    memory_block = "\n".join(f"- {m['text']}" for m in memories) or "(no memory)"
    return f"""You are 42. Use the following persistent memory when replying.

Relevant memory:
{memory_block}

User: {user_msg}
"""
