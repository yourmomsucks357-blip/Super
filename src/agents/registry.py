from typing import Dict, Optional, Type
from .base import BaseAgent


class AgentRegistry:
    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, agent_type: Optional[str] = None):
        """Decorator to register an agent class."""
        def decorator(agent_cls: Type[BaseAgent]) -> Type[BaseAgent]:
            key = agent_type or agent_cls.__name__
            cls._agents[key] = agent_cls
            return agent_cls
        return decorator

    @classmethod
    def get(cls, agent_type: str) -> Type[BaseAgent]:
        if agent_type not in cls._agents:
            raise KeyError(f"Agent type '{agent_type}' not registered. "
                           f"Available: {list(cls._agents.keys())}")
        return cls._agents[agent_type]

    @classmethod
    def list_types(cls) -> list:
        return list(cls._agents.keys())

    @classmethod
    def create(cls, agent_type: str, **kwargs) -> BaseAgent:
        return cls.get(agent_type)(**kwargs)


registry = AgentRegistry()
