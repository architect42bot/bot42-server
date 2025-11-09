
"""
symbolic.py — tiny heuristic for symbolic interpretation (polished minimal build)
"""
from typing import List

KEYWORDS = {
    "love": "heart",
    "fear": "shadow",
    "fire": "flame",
    "machine": "engine",
    "hope": "dawn",
    "truth": "light",
}

def interpret_symbolism(text: str) -> List[str]:
    text = (text or "").lower()
    symbols: List[str] = []
    for k, sym in KEYWORDS.items():
        if k in text:
            symbols.append(sym)
    return symbols
