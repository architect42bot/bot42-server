# bot_42_core/agents/agent_loader.py

from .agent_core import AgentRegistry
from .grok_agent import GrokAgent
# later:
# from .claude_agent import ClaudeAgent
# from .gemini_agent import GeminiAgent

_registry = AgentRegistry()

def load_agents() -> AgentRegistry:
    """
    Instantiate and register all agents exactly once.
    """
    if not _registry.list_agents():
        _registry.register(GrokAgent())
        # _registry.register(ClaudeAgent())
        # _registry.register(GeminiAgent())
    return _registry