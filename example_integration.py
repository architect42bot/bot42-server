from memory import MemoryStore

mem = MemoryStore(path="memory_store.json", autosave=True)

def system_bootstrap():
    boot_facts = [
        ("Project codename is 42 (assistant for Robert).", ["project", "identity"], 0.9),
        ("User prefers step-by-step guidance.", ["preference"], 0.8),
        ("Environment: Replit + Python.", ["env"], 0.7),
    ]
    for text, tags, importance in boot_facts:
        hits = mem.recall(text, k=1, must_tags=tags)
        if not hits or text not in hits[0]["text"]:
            mem.remember(text, tags=tags, importance=importance)

def on_user_message(user_text: str) -> str:
    relevant = mem.recall(user_text, k=5)
    context_lines = [f"- {m['text']}" for m in relevant]
    context = "\n".join(context_lines) if context_lines else "(no prior memory)"
    reply = f"I recalled {len(relevant)} relevant memories:\n{context}\n\nReplying to: {user_text}"
    if "my new phone number is" in user_text.lower():
        mem.remember(user_text, tags=["contact"], importance=0.9)
    return reply

if __name__ == "__main__":
    system_bootstrap()
    print("Stats before:", mem.stats())
    print(on_user_message("Can you remind me what 42 is and where we’re running her?"))
    print("Stats after:", mem.stats())
