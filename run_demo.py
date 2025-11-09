"""
Run this file to simulate a chat turn with memory + reflection.
"""
from reflection_loop import handle_message
from memory import MemoryStore

if __name__ == "__main__":
    mem = MemoryStore()
    print("Before:", mem.stats())
    print(handle_message("Let's prioritize the integration tasks today and tomorrow."))
    print("After:", mem.stats())
    print("Done. Check memory_store.json for persisted items.")
