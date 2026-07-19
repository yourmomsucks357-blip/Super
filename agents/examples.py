"""
Example agents that ship with the system.
Register your own agents here or in separate modules.
"""
import asyncio
from typing import Any

from src.agents.base import AgentContext, BaseAgent
from src.agents.registry import AgentRegistry


@AgentRegistry.register("echo")
class EchoAgent(BaseAgent):
    """Returns whatever is passed as `message`."""

    async def execute(self, context: AgentContext, message: str = "hello", **kwargs) -> Any:
        return {"echo": message, "run_id": context.run_id}


@AgentRegistry.register("sleep")
class SleepAgent(BaseAgent):
    """Sleeps for `seconds` then returns elapsed time."""

    async def execute(self, context: AgentContext, seconds: float = 1.0, **kwargs) -> Any:
        await asyncio.sleep(seconds)
        return {"slept_seconds": seconds}


@AgentRegistry.register("compute")
class ComputeAgent(BaseAgent):
    """Performs a simple computation: sum of a list of numbers."""

    async def execute(self, context: AgentContext, numbers: list = None, **kwargs) -> Any:
        nums = numbers or [1, 2, 3, 4, 5]
        return {"sum": sum(nums), "count": len(nums), "average": sum(nums) / len(nums)}
