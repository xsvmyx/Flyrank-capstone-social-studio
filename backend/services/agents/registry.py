from typing import Type, List
from services.agents.base_agent import BaseAgent


_AGENT_REGISTRY: List[Type[BaseAgent]] = []


def register_agent(cls: Type[BaseAgent]) -> Type[BaseAgent]:
    """
    Decorator used to explicitly register an LLM agent in the pipeline.
    """
    if cls not in _AGENT_REGISTRY:
        _AGENT_REGISTRY.append(cls)
    return cls


def get_registered_agents() -> List[Type[BaseAgent]]:
    """
    Returns the complete list of agent classes registered with @register_agent.
    """
    return _AGENT_REGISTRY

