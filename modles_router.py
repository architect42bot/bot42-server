# chat_pipeline.py (or wherever your reasoning helpers live)

from typing import Tuple
from models_router import (
    ModelName,
    ask_council,
    synthesize_council_answer,
    CouncilTrace,
)


def run_council_reasoning(
    user_prompt: str,
    importance: str = "normal",
) -> Tuple[str, CouncilTrace]:
    """
    Run a council-of-minds pass and return:
    - final answer string (what 42 says to the user)
    - CouncilTrace (for why-log / audits)
    """

    # Decide who to invite to the council.
    # Right now it's just OPENAI_MAIN; later you can add GROK, GEMINI, etc.
    models = [ModelName.OPENAI_MAIN]

    # Example rule: if it's "high" importance, invite more brains
    if importance == "high":
        # Only append these once you’ve wired their APIs
        # models.append(ModelName.GROK)
        # models.append(ModelName.GEMINI)
        # models.append(ModelName.LOCAL_LLAMA)
        pass

    base_system_prompt = (
        "You are one of several models being asked for advice by 42. "
        "Answer honestly and clearly. You will be part of a council; "
        "another process will synthesize the final response."
    )

    trace = ask_council(
        user_prompt=user_prompt,
        models=models,
        system_prompt=base_system_prompt,
    )

    # Now synthesize into a single 42-style answer
    trace = synthesize_council_answer(
        council_trace=trace,
        synthesis_system_prompt=None,  # use default merge prompt from router
    )

    final_answer = trace.synthesis or "Sorry, I could not synthesize a response."
    return final_answer, trace