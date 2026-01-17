# chat_council_endpoint.py

from datetime import datetime, timezone

from fastapi import APIRouter

from chat_pipeline import (
    run_council_reasoning,
    handle_chat,
    ChatRequest,
    ChatResponse,
)

from fast_intents import fast_intent_reply

router = APIRouter()


@router.post("/chat/council", response_model=ChatResponse)
async def chat_with_council(payload: ChatRequest) -> ChatResponse:
    raw = (payload.input or "").strip()

    fast = fast_intent_reply(raw)
    if fast is not None:
        now_utc = datetime.now(timezone.utc)
        return ChatResponse(
            reply=fast,
            session_id=(payload.session_id or ""),
            timestamp=now_utc.isoformat(),
        )

    final_answer, _trace = run_council_reasoning(
        user_prompt=payload.input,
        importance=(payload.importance or "normal"),
    )

    return ChatResponse(
        reply=final_answer,
        session_id=(payload.session_id or ""),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/council/chat", response_model=ChatResponse)
async def council_chat_alias(payload: ChatRequest) -> ChatResponse:
    """
    ⚠ Deprecated.
    Use POST /chat/council instead.
    """
    return await chat_with_council(payload)