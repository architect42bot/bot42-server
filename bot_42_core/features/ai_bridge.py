"""
bridge.py — Central system bridge for AI 42
-------------------------------------------
This module connects 42’s internal subsystems together:
- Core dispatch and event routing
- Personality, memory, and storage modules
- Law system integration (AI42 ↔ LawSystem)
"""

# -------------------------------
# Base Imports
# -------------------------------
from typing import Any
import logging

# -------------------------------
# Import Core 42 Components
# -------------------------------
# Adjust these imports if your actual paths differ
from core.ai42 import AI42Core
from features.personality import Personality
from features.dispatcher import Dispatcher
from features.storage import Storage

# -------------------------------
# Import Law System
# -------------------------------
from new_law_system import LawSystem
from bot_42_core.features.ai42_bridge import AI42 as lawAI


# -------------------------------
# Setup Logging
# -------------------------------
logger = logging.getLogger("bridge")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# -------------------------------
# Bridge Functions
# -------------------------------
def attach_core_components(core: AI42Core) -> None:
    """Attach 42’s main personality, dispatcher, and storage systems."""
    core.personality = Personality()
    core.dispatcher = Dispatcher()
    core.storage = Storage()
    logger.info("✅ Core systems attached: Personality, Dispatcher, Storage.")


def attach_law_system(core: AI42Core) -> None:
    """Attach the LawSystem and AI42 Law bridge to the AI core."""
    core.law_system = LawSystem()
    core.ai_law = LawAI(core.law_system)
    logger.info("⚖️  Law system integrated successfully.")


def initialize_42_core() -> AI42Core:
    """
    Create and fully initialize the AI 42 core system with all bridges.
    Returns a ready-to-run AI42Core instance.
    """
    ai42 = AI42Core()
    attach_core_components(ai42)
    attach_law_sys
