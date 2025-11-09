
import os

def load_scroll(name):
    path = os.path.join("scrolls", name)
    if not os.path.exists(path):
        return f"Scroll '{name}' not found."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def list_scrolls():
    return [f for f in os.listdir("scrolls") if f.endswith(".txt") or f.endswith(".md")]
