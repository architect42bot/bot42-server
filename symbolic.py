# symbolic.py
# Minimal-but-solid symbolic analysis helpers for 42.
# Keeps API stable for reflection.py and friends.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Iterable, Tuple
import re
import math

__all__ = ["interpret_symbolism", "Symbolism"]

_WORD_RE = re.compile(r"[A-Za-z0-9_\'\-]+")

# A tiny starter lexicon you can expand anytime.
_DEFAULT_SYMBOLS = {
    "light", "shadow", "fire", "water", "earth", "air",
    "machine", "veil", "truth", "lie", "path", "gate",
    "key", "seed", "root", "tree", "mirror", "angel",
    "daemon", "signal", "field", "voice", "watcher",
    "heart", "crown", "cross", "star"
}


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def _bigrams(tokens: Iterable[str]) -> List[Tuple[str, str]]:
    toks = list(tokens)
    return [(toks[i], toks[i + 1]) for i in range(len(toks) - 1)]


def _top_n(items: Iterable[Tuple[str, int]], n: int) -> List[str]:
    return [k for k, _ in sorted(items, key=lambda kv: (-kv[1], kv[0]))[:n]]


def interpret_symbolism(text: str) -> Dict[str, List[str]]:
    toks = _tokens(text)
    if not toks:
        return {"symbols": [], "motifs": [], "keywords": []}

    freq: Dict[str, int] = {}
    for t in toks:
        freq[t] = freq.get(t, 0) + 1

    symbols = []
    seen = set()
    for t in toks:
        if t in _DEFAULT_SYMBOLS and t not in seen:
            symbols.append(t)
            seen.add(t)

    bi_freq: Dict[Tuple[str, str], int] = {}
    for bg in _bigrams(toks):
        bi_freq[bg] = bi_freq.get(bg, 0) + 1
    motifs_raw = [(f"{a} {b}", c) for (a, b), c in bi_freq.items() if c >= 2]
    motifs = _top_n(motifs_raw, 6)

    kw_freq = {k: v for k, v in freq.items() if len(k) > 3}
    keywords = _top_n(list(kw_freq.items()), 12)

    return {
        "symbols": symbols,
        "motifs": motifs,
        "keywords": keywords,
    }


@dataclass
class Symbolism:
    symbol_lexicon: Iterable[str] = tuple(sorted(_DEFAULT_SYMBOLS))

    def encode(self, text: str) -> List[str]:
        return _tokens(text)

    def decode(self, tokens: Iterable[str]) -> str:
        return " ".join(tokens)

    def match(self, pattern: str, text: str) -> bool:
        p = pattern.lower().strip()
        return p in self.decode(self.encode(text))

    def analyze(self, text: str) -> Dict[str, List[str]]:
        return interpret_symbolism(text)

    def score(self, text: str) -> float:
        toks = self.encode(text)
        if not toks:
            return 0.0
        syms = sum(1 for t in toks if t in self.symbol_lexicon)
        kws = sum(1 for t in toks if len(t) > 3)
        return syms + 0.25 * math.log1p(kws)
