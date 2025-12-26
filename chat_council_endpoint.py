# main.py (inside your chat endpoint handler)

from fastapi import APIRouter
from chat_pipeline import run_council_reasoning, ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat/council", response_model=ChatResponse)
def chat_with_council(payload: ChatRequest) -> ChatResponse:
    final_answer, council_trace = run_council_reasoning(
        user_prompt=payload.message,
        importance=payload.importance,
    )

    # TODO: wire into your existing why-log / audit log
    # log_council(council_trace.to_dict())

    return ChatResponse(reply=final_answer, timestamp=datetime.utcnow().isoformat())