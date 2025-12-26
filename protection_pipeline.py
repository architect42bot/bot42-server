from typing import Optional, List
from pydantic import BaseModel


class ProtectionTestRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    channel: Optional[str] = None
    tags: Optional[List[str]] = None


def run_protection_guard(
    user_text: str,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    channel: str = "chat",
    tags: Optional[List[str]] = None,
):
    # Temporary stub logic — just echo back the inputs
    return {
        "allowed": True,
        "reason": "stub-allow",
        "echo": {
            "text": user_text,
            "channel": channel,
            "user_id": user_id,
            "user_role": user_role,
            "tags": tags,
        },
    }