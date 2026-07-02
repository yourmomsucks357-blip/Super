"""Planning Plugin — internal cognitive plugin."""
from typing import Any, Dict, List
from src.memory.models import RetrievalResult


class PlanningPlugin:
    """
    Builds an execution plan from retrieved memory context and available agents.
    Internal to the cognitive loop — no external tool access.
    """

    def build_plan(
        self,
        objective: str,
        memory_context: List[RetrievalResult],
        available_agents: List[str],
    ) -> List[Dict[str, Any]]:
        """Return an ordered list of execution steps."""
        steps = []
        # Use top strategy content to inform ordering
        for result in memory_context[:3]:
            item = result.item
            if item.confidence >= 0.5:
                steps.append({
                    "source": "memory",
                    "hint": item.title,
                    "confidence": item.confidence,
                })
        # Append available agent steps
        for agent in available_agents:
            steps.append({"source": "agent", "agent_type": agent})
        return steps
