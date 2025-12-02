from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """
    Base class for all agents (Tutor, Evaluator, Monitor).
    Every agent must implement the .run() method.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main function.
        
        Parameters:
            goal: What the orchestrator wants this agent to do
            context: Data required to complete the goal

        Returns:
            A dictionary containing:
                - "plan" OR "result"
                - "tool_calls" (optional)
                - "metadata" (optional)
        """
        pass

    def __repr__(self):
        return f"<Agent name={self.name}>"