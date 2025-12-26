# chat_pipeline.py

from datetime import datetime, timezone
from pydantic import BaseModel, Field

from reply_engine import generate_reply
from ethics.ethics import christlike_response

from protection_pipeline import run_protection_guard
from nina_pipeline import analyze_nina, log_nina
from collections import defaultdict
from typing import Dict, List, Tuple
from bot_42_core.agents.agent_loader import load_agents
from core.answerability import answerability_gate, Answerability
from bot_42_core.features.speech import speech as speech_module
import asyncio

ConversationTurn = Tuple[str, str]
conversation_logs: Dict[str, List[ConversationTurn]] = defaultdict(list)

async def run_council_reasoning(user_prompt: str, importance: str = "normal"):
    """
    Run the registered agent council and return a final answer + trace.
    """

    registry = load_agents()
    agent_names = registry.list_agents()

    results = []
    for name in agent_names:
        agent = registry.get_agent(name)
        if agent is None:
            continue

        result = await agent.run(
            task=user_prompt,
            context={"importance": importance},
        )
        results.append(result)


class ChatRequest(BaseModel):
    input: str


class ChatResponse(BaseModel):
    reply: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
def handle_chat(user_text: str) -> ChatResponse:
    """
    Wrapper gate in front of the existing run_chat_pipeline.
    Keeps current behavior intact while enabling answerability routing.
    """
    # --- Council override (pre-answerability) ---
    if user_text.startswith("!council:high "):
        user_text = user_text.replace("!council:high ", "", 1)
        final_answer, council_trace = asyncio.run(
            run_council_reasoning(user_prompt=user_text, importance="high")
        )
        return ChatResponse(
            reply=final_answer,
            timestamp=datetime.utcnow().isoformat(),
        )
    if user_text.startswith("!council "):
        user_text = user_text.replace("!council ", "", 1)
        final_answer, council_trace = asyncio.run(
            run_council_reasoning(user_prompt=user_text, importance="normal")
        )
        return ChatResponse(
            reply=final_answer,
            timestamp=datetime.utcnow().isoformat(),
        )
    gate = answerability_gate(user_text)

    if gate.verdict in (Answerability.NEEDS_CLARIFICATION, Answerability.HIGH_STAKES):
        # Return a friendly clarification response using your existing ChatResponse model
        q = "\n".join(f"- {x}" for x in (gate.questions or []))
        notes = gate.notes or ""
        reply = "I need a little more info before I answer.\n"
        if q:
            reply += f"\nQuestions:\n{q}\n"
        if notes:
            reply += f"\nNotes: {notes}\n"
        return ChatResponse(reply=reply)

    if gate.verdict == Answerability.REQUIRES_EXTERNAL_DATA:
        q = "\n".join(f"- {x}" for x in (gate.questions or []))
        notes = gate.notes or ""
        reply = "I don’t have enough verified information to answer that reliably yet.\n"
        if q:
            reply += f"\nWhat would help:\n{q}\n"
        if notes:
            reply += f"\nNotes: {notes}\n"
        return ChatResponse(reply=reply)

    # Otherwise proceed with your existing pipeline unchanged
    return run_chat_pipeline(user_text)

    
def run_chat_pipeline(user_text: str) -> ChatResponse:
    # ---- 1) Protection guard ----
    protection_result = run_protection_guard(
        user_text=user_text,
        channel="chat",
        user_id=None,
        user_role=None,
        tags=None,
    )

    if not protection_result.get("allowed", True):
        safe_message = protection_result.get(
            "safe_message",
            "I'm here with you. Whatever you're facing, you don't have to carry it alone.",
        )
        return ChatResponse(
            reply=safe_message,
            timestamp=datetime.utcnow().isoformat(),
        )

    # ---- 2) NINA analysis ----
    nina = analyze_nina(user_text)
    nina_entry = log_nina(user_text, nina)

    # Optional logging later:
    # with open("nina_log.jsonl", "a") as f:
    #     f.write(json.dumps(nina_entry) + "\n")

    # ---- 3) Conversation ID + recent history ----
    conv_id = "default"  # later we can plug in a real user/session id
    history_text = ""

    if history_text:
        # Feed recent conversation + new message into the model
        model_input = (
            "Recent conversation between the user and 42:\n"
            f"{history_text}\n\n"
            f"User: {user_text}"
        )
    else:
        # First turn – just use the user text
        model_input = user_text

    # ---- 4) Core reply generation (with context) ----
    core_reply = generate_reply(model_input)

    # ---- 5) Update conversation memory (simple 20-turn buffer) ----
    conversation_logs[conv_id].append((user_text, core_reply))
    if len(conversation_logs[conv_id]) > 20:
        conversation_logs[conv_id] = conversation_logs[conv_id][-20:]

    # ---- 6) Return reply ----
    return ChatResponse(
        reply=core_reply,
        timestamp=datetime.utcnow().isoformat(),
    )
