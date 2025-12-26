from abc import ABC, abstractmethod
from typing import Dict, List

class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def run(self, task: str, context: Dict) -> Dict:
        """Run the agent with the given task and context."""
        pass

class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """Register an agent by name."""
        self.agents[agent.name] = agent

    def list_agents(self) -> List[str]:
        """Return a list of registered agent names."""
        return list(self.agents.keys())

    def get_agent(self, name: str) -> BaseAgent:
        """Get an agent by name."""
        return self.agents.get(name)