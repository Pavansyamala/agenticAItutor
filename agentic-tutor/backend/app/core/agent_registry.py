# backend/app/core/agent_registry.py
from typing import Dict
from backend.app.agents.base_agent import BaseAgent

class AgentRegistry:
    """
    Simple registry for agent instances.
    Orchestrator queries this to get agents by role/name.
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, name: str, agent: BaseAgent):
        self._agents[name] = agent

    def get(self, name: str) -> BaseAgent:
        agent = self._agents.get(name)
        if agent is None:
            raise KeyError(f"Agent '{name}' not registered.")
        return agent

    def list_agents(self):
        return list(self._agents.keys())
