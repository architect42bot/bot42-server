# reply_engine.py

from datetime import datetime
from typing import Optional, Any

from bot_42_core.llm_core import generate_llm_reply
# from log_manager import log_chat_turn  # Optional: re-enable later once signature is confirmed
from ethics.christ_ethics import apply_christ_ethics

def decide_tone(nina: Optional[Any], ethics: Optional[Any]) -> str:
    """
    Decide which tone 42 should use based on NINA and ethics.

    Returns one of:
      - "gentle"
      - "wise"
      - "intuitive"
      - "corrective"
    """

    # ----- Ethics check -----
    # If ethics score is strongly negative -> use compassionate corrective tone
    try:
        if ethics and isinstance(ethics, dict):
            if ethics.get("score", 0.0) <= -0.5:
                return "corrective"
    except Exception as exc:
        print(f"[reply_engine] ethics tone check failed: {exc!r}")

    # ----- Emotional needs check (from NINA) -----
    needs = []
    try:
        if nina is not None:
            needs = getattr(nina, "needs", []) or []
    except Exception as exc:
        print(f"[reply_engine] NINA needs access failed: {exc!r}")

    if "comfort" in needs or "reassurance" in needs:
        return "gentle"

    if "clarity" in needs or "understanding" in needs:
        return "wise"

    # ----- Philosophical / identity / meaning search -----
    flags = []
    try:
        if nina is not None:
            flags = getattr(nina, "narrative_flags", []) or []
    except Exception as exc:
        print(f"[reply_engine] NINA narrative_flags access failed: {exc!r}")

    if "identity_search" in flags or "meaning_search" in flags:
        return "intuitive"

    # ----- Default fallback -----
    return "gentle"


def generate_reply(
    text: str,
    nina: Optional[Any] = None,
    ethics: Optional[Any] = None,
) -> str:
    """
    Main 42 reply engine.

    Uses NINA + ethics to pick a tone, then delegates to the core LLM brain.
    If anything breaks, returns a safe, human-readable fallback string.
    """

    try:
        # Decide tone from NINA + ethics
        tone = decide_tone(nina, ethics)

        # Delegate actual LLM call to the core brain
        reply = generate_llm_reply(
            user_text=text,
            tone=tone,
            nina=nina,
            ethics=ethics,
        )
        reply = apply_christ_ethics(reply, nina)

        # Ensure we always return a clean string
        if not isinstance(reply, str) or not reply.strip():
            print("[reply_engine] Empty or non-string reply from LLM core")
            return (
                "I'm here with you, but I'm having trouble forming a reply right now. "
                "Could you try asking that in a slightly different way?"
            )

        # Optional: log the turn (disabled for now to avoid signature mismatches)
        # try:
        #     log_chat_turn(
        #         user_text=text,
        #         reply_text=reply,
        #         nina_state=getattr(nina, '__dict__', None),
        #         ethics_state=ethics,
        #         timestamp=datetime.utcnow().isoformat(),
        #     )
        # except Exception as log_err:
        #     print(f'[reply_engine] log_chat_turn failed: {log_err!r}')

        return reply.strip()

    except Exception as e:
        print(f"[42 ERROR] llm call failed in generate_reply: {e!r}")
        return (
            "[42 core] I ran into a problem talking to my LLM brain, "
            "but I still heard you. Please try asking again in a moment."
        )