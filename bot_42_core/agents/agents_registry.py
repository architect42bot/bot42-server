from bot_42_core.agents.agent_core import AgentRegistry
from bot_42_core.agents.grok_agent import GrokAgent

registry = AgentRegistry()
registry.register(GrokAgent())