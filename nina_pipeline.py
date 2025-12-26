# nina_pipeline.py

from datetime import datetime
from pydantic import BaseModel
from typing import Dict, List, Tuple
from collections import defaultdict

ConversationTurn = Tuple[str, str]
conversation_logs: Dict[str, List[ConversationTurn]] = defaultdict(list)

def build_history(conv_id: str, max_turns: int = 6) -> str:
    """
    Turn the recent conversation into a plain-text history string
    that we can pass into generate_reply.
    """
    turns = conversation_logs.get(conv_id, [])[-max_turns:]
    if not turns:
        return ""

    lines: List[str] = []
    for user_msg, bot_msg in turns:
        lines.append(f"User: {user_msg}")
        lines.append(f"42: {bot_msg}")
    return "\n".join(lines)

class NinaInsight(BaseModel):
    needs: List[str]
    interests: List[str]
    narrative_flags: List[str]
    agency_flags: List[str]


def analyze_nina(user_text: str) -> NinaInsight:
    """
    Temporary placeholder version of NINA until we fully restore your original logic.
    Later, we'll bring back the real pattern analysis.
    """

    text = (user_text or "").lower()

    needs = []
    interests = []
    narrative_flags = []
    agency_flags = []

    # SIMPLE STARTER LOGIC — will replace with the full version
    if "i need" in text:
        needs.append("direct_need")
    if "i want" in text:
        interests.append("desire")
    if "i feel" in text:
        narrative_flags.append("emotion")
    if "i will" in text:
        agency_flags.append("commitment")

    # fallback so lists are never empty
    if not needs:
        needs.append("unknown")
    if not interests:
        interests.append("unknown")
    if not narrative_flags:
        narrative_flags.append("none_detected")
    if not agency_flags:
        agency_flags.append("none_detected")

    return NinaInsight(
        needs=needs,
        interests=interests,
        narrative_flags=narrative_flags,
        agency_flags=agency_flags,
    )


def log_nina(text: str, nina: NinaInsight):
    """Optional logging helper to JSON line format."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "text": text,
        "needs": nina.needs,
        "interests": nina.interests,
        "narrative_flags": nina.narrative_flags,
        "agency_flags": nina.agency_flags,
    }
    return entry

