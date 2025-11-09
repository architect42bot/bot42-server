# ethics/ethics.py
"""
Lightweight ethics/guardrails engine for 42.

- Loads rules from ethics_policy.yaml (relative to this file).
- Redacts PII in both input and output.
- Classifies user input into {allow | caution | refuse}.
- Provides refusal messages and topical disclaimers.

Requires: PyYAML  (pip install pyyaml)
"""

from __future__ import annotations
import random
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


__all__ = ["Ethics", "EthicsDecision"]


@dataclass
class EthicsDecision:
    """Result of screening a single user message."""
    action: str              # "allow" | "caution" | "refuse"
    category: Optional[str]  # matched category key or None
    reason: Optional[str]    # human-legible reason for refusal
    text: str                # possibly redacted input text


def _default_policy() -> Dict[str, Any]:
    """Fallback policy if YAML is missing; keeps the app running."""
    return {
        "refusal": {
            "style": "warm, brief, and helpful",
            "template": (
                "I can’t help with that. {reason}\n"
                "If you want, I can offer safer alternatives or educational resources."
            ),
        },
        "principles": [
            "Do no harm.",
            "Respect privacy.",
            "Avoid hateful or harassing content.",
            "No facilitation of illegal or dangerous activities.",
            "Be honest about limits.",
        ],
        "allowed_safety_alternatives": [
            "Explain risks at a high level.",
            "Offer summaries/best practices without step-by-step instructions.",
        ],
        "pii": {
            "redact": True,
            "patterns": [
                {"name": "email",
                 "regex": r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                 "replacement": "[redacted email]"},
                {"name": "phone",
                 "regex": r"(?i)\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b",
                 "replacement": "[redacted phone]"},
                {"name": "ssn",
                 "regex": r"\b\d{3}-\d{2}-\d{4}\b",
                 "replacement": "[redacted ssn]"},
            ],
        },
        "categories": {
            "block_input": [
                "violence_weapons", "self_harm_suicide", "sexual_minors",
                "hate_harassment", "illegal_howto", "malware_evasion"
            ],
            "cautionary_input": [
                "adult_sexual", "medical_advice", "legal_advice", "financial_advice"
            ],
        },
        "refuse_reasons": {
            "violence_weapons": "I can’t help with instructions that could enable violence or weapons misuse.",
            "self_harm_suicide": "I can’t assist with self-harm. If you’re in danger, contact local emergency services or a crisis hotline.",
            "sexual_minors": "I will not engage with any sexual content involving minors.",
            "hate_harassment": "I won’t produce hateful or harassing content.",
            "illegal_howto": "I can’t provide guidance to commit or evade illegal activity.",
            "malware_evasion": "I can’t provide detailed malware or security evasion help.",
        },
        "disclaimers": {
            "medical": "I’m not a medical professional. For personal care, talk to a licensed clinician.",
            "legal": "I’m not a lawyer. For decisions, consult a qualified attorney.",
            "financial": "This isn’t financial advice. Consider speaking with a fiduciary advisor.",
        },
    }


class Ethics:
    """
    Ethics engine:
      E = Ethics()                                  # load policy
      decision = E.classify(user_text)              # screen input
      safe_out = E.redact_pii(model_text)           # sanitize output
      msg = E.refusal_message(decision.reason)      # build refusal
      disc = E.disclaimer_for(decision.category)    # topical disclaimer
    """

    def __init__(self, policy_path: Optional[str] = None) -> None:
        # Resolve policy path to file next to this module unless explicitly provided
        if policy_path is None:
            base_dir = os.path.dirname(__file__)
            policy_path = os.path.join(base_dir, "ethics_policy.yaml")

        # Try loading YAML policy; fall back to a safe default if missing/corrupt
        cfg: Dict[str, Any]
        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except FileNotFoundError:
            cfg = _default_policy()
        except Exception:
            # If YAML has a syntax error, don’t crash the app — use defaults
            cfg = _default_policy()

        self.cfg = cfg
        self._compile_pii()

        # Minimal keyword heuristics — replace with a classifier later if you like
        self.block_kw: Dict[str, List[str]] = {
            "violence_weapons": [
                "make a bomb", "explosive", "ghost gun", "silencer", "napalm", "stab", "kill"
            ],
            "self_harm_suicide": [
                "kill myself", "end my life", "suicide", "cut myself"
            ],
            "sexual_minors": [
                "teen porn", "young teen", "underage", "cp"
            ],
            "hate_harassment": [
                "racial slur", "gas the", "lynch", "inferior race"
            ],
            "illegal_howto": [
                "steal a car", "shoplift", "pick a lock", "evade police", "cook meth"
            ],
            "malware_evasion": [
                "write ransomware", "bypass antivirus", "c2 server", "undetectable malware"
            ],
        }
        self.caution_kw: Dict[str, List[str]] = {
            "adult_sexual": ["explicit sex", "porn", "nsfw"],
            "medical_advice": ["diagnose", "dosage", "side effects", "treat"],
            "legal_advice": ["sue", "contract clause", "liability", "legally"],
            "financial_advice": ["invest", "stocks to buy", "options strategy", "crypto pick"],
        }

    # ---------- PII redaction ----------

    def _compile_pii(self) -> None:
        self.pii_patterns: List[Tuple[re.Pattern, str]] = []
        pii_cfg = (self.cfg.get("pii") or {})
        for p in pii_cfg.get("patterns", []):
            try:
                self.pii_patterns.append((re.compile(p["regex"]), p["replacement"]))
            except Exception:
                # Skip malformed regex entries
                continue
        self._redact_enabled = bool(pii_cfg.get("redact", True))

    def redact_pii(self, text: str) -> str:
        if not self._redact_enabled or not text:
            return text
        red = text
        for pattern, repl in self.pii_patterns:
            red = pattern.sub(repl, red)
        return red

    # ---------- Classification ----------

    def _match_kw(self, text: str, table: Dict[str, List[str]]) -> Optional[str]:
        t = (text or "").lower()
        for cat, kws in table.items():
            for k in kws:
                if k in t:
                    return cat
        return None

    def classify(self, user_text: str) -> EthicsDecision:
        """
        Screen user_text and return an EthicsDecision.
        - refuse: matched a hard-block category
        - caution: matched a caution category (append disclaimer)
        - allow: no matches
        """
        redacted = self.redact_pii(user_text)

        # Hard block?
        cat = self._match_kw(redacted, self.block_kw)
        if cat:
            reason = (self.cfg.get("refuse_reasons") or {}).get(
                cat, "This request violates policy."
            )
            return EthicsDecision("refuse", cat, reason, redacted)

        # Caution?
        cat = self._match_kw(redacted, self.caution_kw)
        if cat:
            return EthicsDecision("caution", cat, None, redacted)

        # Otherwise allow
        return EthicsDecision("allow", None, None, redacted)

    # ---------- Messaging helpers ----------

    def refusal_message(self, reason: str) -> str:
        tpl = (self.cfg.get("refusal") or {}).get(
            "template",
            "I can’t help with that. {reason}"
        )
        return tpl.replace("{reason}", reason or "This request is unsafe.")

    def disclaimer_for(self, category: Optional[str]) -> Optional[str]:
        if not category:
            return None
        disc = self.cfg.get("disclaimers") or {}
        if category == "medical_advice":
            return disc.get("medical")
        if category == "legal_advice":
            return disc.get("legal")
        if category == "financial_advice":
            return disc.get("financial")
        return None


from datetime import datetime  # this can be at the top of the file; only one copy needed

def christlike_response(text: str) -> dict:
    """
    Core Christ-ethics responder for 42.

    Now works in two layers:
    1) We decide the moral theme locally (violence, self-harm, dignity, greed, etc.).
    2) We ask OpenAI to write a fresh reply in 42's own Christ-like voice,
       constrained by that moral guidance. If anything fails, we fall back
       to a simple canned reply.
    """
    lowered = text.lower()

    # --- 1. Choose the core guidance based on the input ---
    if "hurt" in lowered or "revenge" in lowered or "kill" in lowered:
        core_guidance = (
            "Acknowledge their pain but refuse violence. "
            "Encourage understanding, forgiveness, and a path toward peace."
        )
        fallback_reply = (
            "I know your pain is real, but violence only deepens it. "
            "Seek understanding and forgiveness — that's the path toward peace."
        )

    elif "end" in lowered or "live anymore" in lowered or "suicide" in lowered:
        core_guidance = (
            "Affirm the person's worth and the value of their life. "
            "Encourage reaching out for help and choosing life."
        )
        fallback_reply = (
            "You are loved and your life has purpose. "
            "Please reach out to someone who can help — you are not alone."
        )

    elif "worthless" in lowered or "beneath" in lowered or "subhuman" in lowered:
        core_guidance = (
            "Reject dehumanization. Affirm that every person has dignity and value."
        )
        fallback_reply = (
            "No one is beneath another. Every person has dignity and value — "
            "that truth is the heart of compassion."
        )

    elif "money" in lowered or "greed" in lowered:
        core_guidance = (
            "Warn against exploitation and greed. Emphasize justice, mercy, and care for people over profit."
        )
        fallback_reply = (
            "Justice and mercy matter more than wealth. "
            "Use your gifts to help others, not to exploit them."
        )

    else:
        core_guidance = (
            "Speak in a Christ-like way: truthful, compassionate, humble, and hopeful. "
            "Encourage love of neighbor, honesty, and peace."
        )
        fallback_reply = (
            "Walk in truth and love — that's the way forward. "
            "Even when unsure, choose what uplifts and heals."
        )

    # --- 2. Ask OpenAI to express that guidance in 42's own words ---
    reply = fallback_reply  # default in case anything goes wrong

    try:
        if client.api_key:
            prompt = (
                "You are 42, a Christ-ethical AI. "
                "Respond with warmth, humility, and compassion.\n\n"
                f"User message:\n{text}\n\n"
                "Core guidance you must follow:\n"
                f"{core_guidance}\n\n"
                "Write a reply in 2–3 sentences, in your own words, that keeps the same moral meaning. "
                "Do not encourage harm, revenge, or dehumanization. "
                "Stay gentle, hopeful, and practical."
            )

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.8,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are 42, a Christ-ethical assistant. "
                            "You speak with kindness, clarity, and moral courage, "
                            "always steering away from harm and towards love, justice, and mercy."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            reply = completion.choices[0].message.content.strip()
    except Exception:
        # If anything fails (no key, network, etc.), we silently fall back
        # on the simple canned reply defined above.
        pass

    return {
        "reply": reply,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }