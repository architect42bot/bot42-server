# ============================================================
# 42 CLI Commands — Bot Core
# ============================================================

from bot_42_core.features.personality import load_personality
from bot_42_core.features.itinerary import Task, TaskRunner
from bot_42_core.features.actions import fetch_data, post_update

from datetime import datetime, timedelta


# ------------------------------------------------------------
# Simple Personality Interface (for CLI testing)
# ------------------------------------------------------------
def say_as(persona_key: str, text: str) -> str:
    """
    Load the specified personality and have it reply to text.
    """
    p = load_personality(persona_key)
    out = p.reply(text)
    return out["text"]


# ------------------------------------------------------------
# Default Itinerary Runner
# ------------------------------------------------------------
def run_default_itinerary() -> int:
    """
    Build and run the default 42 itinerary once.
    Returns the number of tasks that ran.
    """
    now = datetime.now()

    # Define 42's core workflow
    itinerary = [
        Task("Review Incoming Data", now, 60, fetch_data,
             {"fetch": True, "post": False}),
        Task("Analyze Trends", now + timedelta(minutes=60), 60,
             fetch_data, {"fetch": True}),
        Task("Post Updates", now + timedelta(minutes=120), 60,
             post_update, {"fetch": False, "post": True}),
        Task("Summarize Findings", now + timedelta(minutes=180), 60,
             fetch_data, {"fetch": True}),
    ]

    # Execute
    runner = TaskRunner()
    for t in itinerary:
        runner.add(t)

    # Run all tasks that are due
    count = runner.run_due()
    return count