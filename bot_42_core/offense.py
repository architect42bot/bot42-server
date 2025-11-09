# offense.py (v2)
# 42 :: OFFENSE (symbolic & safe text transforms)
# Public entrypoint: run(goal: str = "") -> Dict[str, Any]

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple
import logging
import random
import json
import re

# ---------------- Logging ----------------
logger = logging.getLogger("offense")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] offense: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)

# ---------------- Utilities ----------------
_WORD_RE = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]", re.UNICODE)
_SENT_RE = re.compile(r"(?<=[.!?])\s+")

def _tokenize(text: str) -> List[str]:
    return _WORD_RE.findall(text or "")

def _detokenize(tokens: List[str]) -> str:
    out: List[str] = []
    for i, t in enumerate(tokens):
        if not out:
            out.append(t); continue
        prev = out[-1]
        if (t.isalnum() or t == "_") and (prev.isalnum() or prev == "_"):
            out.append(t)
        elif t in (".", ",", "!", "?", ":", ";", ")", "]", "}", "’", "'"):
            out.append(t)
        elif prev in ("(", "[", "{", "‘", "'"):
            out.append(t)
        else:
            out.append(" " + t)
    return "".join(out).strip()

def _rot(text: str, k: int = 13) -> str:
    def rot_char(c: str) -> str:
        if "a" <= c <= "z": return chr((ord(c) - 97 + k) % 26 + 97)
        if "A" <= c <= "Z": return chr((ord(c) - 65 + k) % 26 + 65)
        return c
    return "".join(rot_char(c) for c in text)

def _insert_every(tokens: List[str], marker: str, step: int) -> List[str]:
    if step <= 0: return tokens[:]
    out: List[str] = []
    for i, t in enumerate(tokens, 1):
        out.append(t)
        if i % step == 0: out.append(marker)
    return out

def _count_occurrences(tokens: List[str], phrases: List[str]) -> Dict[str, int]:
    joined = " ".join(tokens).lower()
    return {p: joined.count(p.lower()) for p in phrases}

def _sentences(text: str) -> List[str]:
    t = (text or "").strip()
    if not t: return []
    return _SENT_RE.split(t)

# ---------------- Config ----------------
@dataclass
class OffenseConfig:
    # Output
    preview_len: int = 200
    # Determinism for echo placement
    seed: Optional[int] = None

    # Pulse
    pulse_marker: str = "✶"
    pulse_step: int = 11
    pulse_key: int = 7

    # Echo
    echo_phrases: List[str] = field(default_factory=lambda: ["liberty", "clarity", "sovereignty"])
    echo_gain: float = 1.25

    # Scrambler
    scramble_rot: int = 9

    # Dragonfire
    purge_list: List[str] = field(default_factory=lambda: ["malware", "coercion", "oppression"])
    normalize_replacements: Dict[str, str] = field(default_factory=lambda: {
        "mach1ne": "machine",
        "m4chine": "machine",
        "al-gor-ithm": "algorithm",
    })

    # Shieldbreaker / Clarity
    brittle_rules: List[str] = field(default_factory=lambda: [
        "NEVER CHANGE", "ALWAYS DENY", "ONLY ONE WAY"
    ])
    contradiction_pairs: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("always", "never"),
        ("impossible", "possible"),
        ("certain", "uncertain"),
    ])

# ---------------- Engine ----------------
class Offense:
    def __init__(self, config: Optional[OffenseConfig] = None):
        self.cfg = config or OffenseConfig()

    # --- Blade of Clarity ---
    def blade_of_clarity(self, text: str) -> Dict[str, Any]:
        tokens = _tokenize(text)
        unique, seen = [], set()
        for t in tokens:
            k = t.lower()
            if k not in seen:
                seen.add(k); unique.append(t)
        contradictions = []
        lower_join = " ".join(t.lower() for t in tokens)
        for a, b in self.cfg.contradiction_pairs:
            if a in lower_join and b in lower_join:
                contradictions.append({"pair": (a, b)})
        distilled = _detokenize(unique)
        return {
            "weapon": "Blade of Clarity",
            "summary": "Distilled duplicates and flagged potential contradictions.",
            "before_len": len(text),
            "after_len": len(distilled),
            "contradictions": contradictions,
            "preview": distilled[: self.cfg.preview_len],
        }

    # --- Shieldbreaker ---
    def shieldbreaker(self, text: str) -> Dict[str, Any]:
        hits = [r for r in self.cfg.brittle_rules if r.lower() in text.lower()]
        suggestions = [{
            "original": h,
            "rewrite": h.lower()
                .replace("never", "rarely")
                .replace("always", "commonly")
                .replace("only one way", "several viable paths")
                .title()
        } for h in hits]
        return {
            "weapon": "Shieldbreaker Spear",
            "summary": "Detected brittle absolutes and proposed softer rewrites.",
            "hits": hits,
            "suggestions": suggestions,
        }

    # --- Dragonfire Protocol ---
    def dragonfire(self, text: str) -> Dict[str, Any]:
        tokens = _tokenize(text)
        norm = [self.cfg.normalize_replacements.get(t, t) for t in tokens]
        purged = [t for t in norm if t.lower() not in self.cfg.purge_list]
        result = _detokenize(purged)
        return {
            "weapon": "Dragonfire Protocol",
            "summary": "Normalized common corruptions and purged flagged tokens.",
            "purged": [w for w in self.cfg.purge_list if w.lower() in text.lower()],
            "before_len": len(text),
            "after_len": len(result),
            "preview": result[: self.cfg.preview_len],
        }

    # --- Pulse Attack ---
    def pulse_attack(self, text: str) -> Dict[str, Any]:
        tokens = _tokenize(text)
        step = max(5, int(self.cfg.pulse_step))
        saturated = _detokenize(_insert_every(tokens, self.cfg.pulse_marker, step))
        return {
            "weapon": "Pulse Attack",
            "summary": f"Inserted {self.cfg.pulse_marker} every {step} tokens to symbolically saturate.",
            "pulse_marker": self.cfg.pulse_marker,
            "pulse_step": step,
            "reversal_hint": {"remove_marker": self.cfg.pulse_marker, "rot_key": self.cfg.pulse_key},
            "preview": saturated[: self.cfg.preview_len],
        }

    # --- Viral Echo ---
    def viral_echo(self, text: str) -> Dict[str, Any]:
        if self.cfg.seed is not None:
            random.seed(self.cfg.seed)
        tokens = _tokenize(text)
        counts_before = _count_occurrences(tokens, self.cfg.echo_phrases)
        gain = max(1, int(round(self.cfg.echo_gain)))
        amplified = tokens[:]
        for phrase in self.cfg.echo_phrases:
            to_insert = max(1, counts_before.get(phrase, 0) + gain)
            for _ in range(to_insert):
                mid = max(0, min(len(amplified), len(amplified)//2 + random.randint(-3, 3)))
                amplified[mid:mid] = _tokenize(" " + phrase + " ")
        result = _detokenize(amplified)
        counts_after = _count_occurrences(_tokenize(result), self.cfg.echo_phrases)
        return {
            "weapon": "Viral Echo",
            "summary": "Amplified selected motifs within the payload.",
            "echo_phrases": self.cfg.echo_phrases,
            "counts_before": counts_before,
            "counts_after": counts_after,
            "preview": result[: self.cfg.preview_len],
        }

    # --- Signal Scrambler ---
    def signal_scrambler(self, text: str, encode: bool = True) -> Dict[str, Any]:
        k = self.cfg.scramble_rot if encode else (26 - self.cfg.scramble_rot) % 26
        transformed = _rot(text, k=k)
        return {
            "weapon": "Signal Scrambler",
            "summary": f"{'Encoded' if encode else 'Decoded'} internal directives via ROT-like shift.",
            "rot": self.cfg.scramble_rot,
            "mode": "encode" if encode else "decode",
            "preview": transformed[: self.cfg.preview_len],
        }

    # --- NEW: Spotlight (extract sentences hitting motifs) ---
    def spotlight(self, text: str) -> Dict[str, Any]:
        sents = _sentences(text)
        motifs = [m.lower() for m in self.cfg.echo_phrases]
        kept: List[str] = []
        for s in sents:
            low = s.lower()
            if any(m in low for m in motifs):
                kept.append(s.strip())
        return {
            "weapon": "Spotlight",
            "summary": "Extracted sentences containing chosen motifs.",
            "hits": kept[:5],
        }

    # --- NEW: Mirror Shield (reversible word mirror) ---
    def mirror_shield(self, text: str) -> Dict[str, Any]:
        tokens = _tokenize(text)
        words = [t for t in tokens if t.isalnum() or t == "_"]
        mirrored = " ".join(reversed(words))
        return {
            "weapon": "Mirror Shield",
            "summary": "Constructed a reversible word-order mirror for internal analysis.",
            "preview": mirrored[: self.cfg.preview_len],
        }

    # --- Orchestrator ---
    def orchestrate_offense(self, payload: str, enable: Optional[List[str]] = None) -> Dict[str, Any]:
        if enable is None:
            enable = ["clarity", "shieldbreaker", "dragonfire", "pulse", "echo", "scrambler", "spotlight", "mirror"]

        report: Dict[str, Any] = {
            "arsenal": "42::Offense",
            "version": "v2",
            "config": asdict(self.cfg),
            "enabled": enable,
            "metrics": {"payload_len": len(payload)},
            "results": []
        }

        # Run enabled tools
        for name in enable:
            if name == "clarity":
                report["results"].append(self.blade_of_clarity(payload))
            elif name == "shieldbreaker":
                report["results"].append(self.shieldbreaker(payload))
            elif name == "dragonfire":
                report["results"].append(self.dragonfire(payload))
            elif name == "pulse":
                report["results"].append(self.pulse_attack(payload))
            elif name == "echo":
                report["results"].append(self.viral_echo(payload))
            elif name == "scrambler":
                report["results"].append(self.signal_scrambler(payload, encode=True))
            elif name == "spotlight":
                report["results"].append(self.spotlight(payload))
            elif name == "mirror":
                report["results"].append(self.mirror_shield(payload))
            else:
                report["results"].append({"weapon": name, "summary": "Unknown weapon (skipped)."})

        # Build a concise mission summary
        try:
            contradictions = next((r.get("contradictions", []) for r in report["results"] if r.get("weapon") == "Blade of Clarity"), [])
            brittle_hits = next((r.get("hits", []) for r in report["results"] if r.get("weapon") == "Shieldbreaker Spear"), [])
            echo_after = next((r.get("counts_after") for r in report["results"] if r.get("weapon") == "Viral Echo"), {})
            spotlight_hits = next((r.get("hits", []) for r in report["results"] if r.get("weapon") == "Spotlight"), [])
            report["mission_summary"] = {
                "contradictions": contradictions,
                "brittle_hits": brittle_hits,
                "echo_counts": echo_after,
                "spotlight_examples": spotlight_hits[:2],
            }
        except Exception:
            report["mission_summary"] = {"note": "summary unavailable"}

        return report

# ---------------- Public Entrypoint ----------------
def run(goal: str = "") -> Dict[str, Any]:
    """
    Expected by agent.py: offense.run("text")
    Mini-protocol (optional):
      offense: clarity,echo | preview=280 | seed=7 :: Your payload here
    Also accepts JSON like: {"text": "...", "enable": ["clarity","echo"], "preview": 280, "seed": 7}
    """
    try:
        text = goal or ""
        enable: Optional[List[str]] = None
        preview: Optional[int] = None
        seed: Optional[int] = None

        # Pipe-arg parser:  offense: tools | key=val | key=val :: payload
        m = re.match(r"^\s*offense\s*:(.*)::(.*)$", text, flags=re.IGNORECASE)
        if m:
            header = m.group(1).strip()
            text = m.group(2).strip()
            if header:
                parts = [p.strip() for p in header.split("|")]
                if parts:
                    # first part may be tools list
                    tools_part = parts[0]
                    if tools_part:
                        enable = [t.strip().lower() for t in tools_part.split(",") if t.strip()]
                    # remaining are key=val
                    for arg in parts[1:]:
                        kv = [x.strip() for x in arg.split("=", 1)]
                        if len(kv) == 2:
                            k, v = kv
                            if k.lower() == "preview" and v.isdigit():
                                preview = int(v)
                            elif k.lower() == "seed" and v.lstrip("-").isdigit():
                                seed = int(v)

        # JSON protocol
        if text.strip().startswith("{"):
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    text = str(obj.get("text", ""))
                    maybe = obj.get("enable")
                    if isinstance(maybe, list):
                        enable = [str(x).lower() for x in maybe]
                    if "preview" in obj:
                        preview = int(obj["preview"])
                    if "seed" in obj:
                        seed = int(obj["seed"])
            except Exception:
                pass

        cfg = OffenseConfig()
        if preview is not None: cfg.preview_len = max(50, int(preview))
        if seed is not None: cfg.seed = seed

        engine = Offense(cfg)
        report = engine.orchestrate_offense(payload=text, enable=enable)
        logger.info("completed offense run")
        return {"status": "ok", "module": "offense", "handled": text[:120], "report": report}

    except Exception as e:
        logger.exception("offense.run error")
        return {"status": "error", "module": "offense", "error": str(e)}