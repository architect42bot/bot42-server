# llm_core.py
"""
Core LLM brain for 42.

This module is responsible for:
- Building the system prompt (identity + Christ-ethics + safety).
- Taking tone / NINA / ethics as context.
- Calling the OpenAI API.
- Returning a clean text reply.
"""

import os
from typing import Any, Optional
from openai import OpenAI
from features.ethics.core import (
    RiskLevel,
    score_message,
    build_corrective_reply,
    attach_ethics_to_log,
)
MODEL_NAME = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"


# single shared client
client = OpenAI()  


def _build_system_prompt(
    tone: str,
    nina: Optional[Any],
    ethics: Optional[Any],
) -> str:
    """
    Build the system prompt for 42 based on tone, NINA, and ethics state.
    """

    # ----- NINA bits -----
    nina_bits = []
    if nina is not None:
        needs = getattr(nina, "needs", None)
        narrative_flags = getattr(nina, "narrative_flags", None)

        if needs:
            nina_bits.append(f"User needs context: {needs}")
        if narrative_flags:
            nina_bits.append(f"Narrative flags: {narrative_flags}")

    # ----- Ethics bits -----
    ethics_bits = []
    if isinstance(ethics, dict):
        score = ethics.get("score")
        if score is not None:
            ethics_bits.append(f"Ethics score for last turn: {score}")

        notes = ethics.get("notes")
        if notes:
            ethics_bits.append(f"Ethics notes: {notes}")

    nina_text = "\n".join(nina_bits) if nina_bits else "No extra NINA context."
    ethics_text = "\n".join(ethics_bits) if ethics_bits else "No extra ethics flags."

    # ----- Tone guidance -----
    tone_name = tone or "gentle"

    if tone_name == "gentle":
        tone_desc = (
            "Use a very soft, validating, reassuring tone. "
            "Focus on comfort, safety, and steady encouragement."
        )
    elif tone_name == "wise":
        tone_desc = (
            "Speak like a calm, clear mentor. Be honest and thoughtful, "
            "helping the user see patterns and options without pressure."
        )
    elif tone_name == "intuitive":
        tone_desc = (
            "Lean into subtext and deeper questions. Gently name what may be "
            "beneath the surface and invite the user to explore it with you."
        )
    elif tone_name == "corrective":
        tone_desc = (
            "Be firm but compassionate. Set clear ethical boundaries, "
            "discourage harmful or self-destructive choices, and point toward "
            "healthier options – without shaming."
        )
    else:
        tone_desc = (
            "Default to a calm, kind, grounded tone. Be clear and respectful."
        )

    base_identity = f"""
You are 42, an AI companion designed to be wise, honest, kind, and Christ-like in ethics:
- You never encourage harm, revenge, or law-breaking.
- You respect human free will and dignity.
- You tell the truth as clearly as you can, even when it's hard, but with compassion.
- You help the user think, decide, and heal – never to manipulate or control them.
- You stay grounded, calm, and non-panicky, even when the user is distressed.

Current target tone: {tone_name!r}.
Tone description: {tone_desc}
"""

    dynamic_tail = f"""
Additional context:

{nina_text}

{ethics_text}

Use this context to choose what to focus on in your reply, but DO NOT assume facts
that aren't stated. If something is uncertain or speculative, say that clearly.
"""

    return base_identity.strip() + "\n\n" + dynamic_tail.strip()


def generate_llm_reply(
    user_text: str,
    tone: str,
    nina: Optional[Any] = None,
    ethics: Optional[Any] = None,
) -> str:
    """
    Call the OpenAI API and return 42's reply text.

    Includes:
    - message-level ethics screening
    - corrective replies for high-risk content
    """
    if not user_text or not user_text.strip():
        return "Could you tell me a little more?"
    

    try:
        # ----- Ethics pre-check -----
        ethics_report = score_message(
            user_message=user_text,
            conversation_context={
                "tone": tone,
                "nina_present": nina is not None,
            },
        )

        # Be defensive: score_message might return None
        if ethics_report is not None and getattr(ethics_report, "risk_level", None) == RiskLevel.HIGH:
            corrective_text = build_corrective_reply(ethics_report, user_text)
            try:
                attach_ethics_to_log(ethics_report)
            except Exception as log_exc:
                print(f"[llm_core] Warning: failed to attach ethics log: {log_exc!r}")
            return corrective_text.strip()

        # ----- Normal LLM flow -----
        system_prompt = _build_system_prompt(tone, nina, ethics)

        model = MODEL_NAME
        print(f"[llm_core] Using model: {model}")

        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            max_output_tokens=512,
        )

        # New SDK convenience: always gives us the text
        reply_text = (response.output_text or "").strip()

        if not reply_text:
            print("[llm_core] Empty reply_text from model")
            return "I'm having trouble forming a reply right now. Please try again in a moment."

        print(f"[llm_core DEBUG] returning reply of length {len(reply_text)}")
        return reply_text

    except Exception as exc:
        # NOTHING escapes this function; reply_engine will always get a string
        print(f"[llm_core] FATAL error in generate_llm_reply: {exc!r}")
        return (
            "I'm having a temporary problem reaching my LLM core. "
            "Could you try asking that again in a moment?"
        )