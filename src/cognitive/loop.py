"""
Nine Questions Cognitive Loop.

The cognitive layer evaluates every execution context by passing it
through nine structured questions before committing to an action.
Internal cognitive plugins are strictly isolated from external execution
tools — no external tool may import or modify the cognitive runtime.

The nine questions:
    1. What is the current objective?
    2. What memory context is relevant?
    3. What agents and tools are available?
    4. What is the current execution state?
    5. What constraints and guardrails apply?
    6. What is the safest execution path?
    7. What risks exist in this path?
    8. What is the expected outcome?
    9. Proceed, pause for human review, or abort?
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.memory.models import MemoryItem, RetrievalResult
from src.memory.retriever import retrieve
from src.config import settings


class CognitiveDecision(str, Enum):
    PROCEED = "proceed"
    PAUSE   = "pause"    # human-in-the-loop gate
    ABORT   = "abort"


@dataclass
class CognitiveState:
    """Snapshot of the cognitive loop at one evaluation cycle."""
    objective:        str                    = ""
    memory_context:   List[RetrievalResult]  = field(default_factory=list)
    available_agents: List[str]              = field(default_factory=list)
    execution_state:  Dict[str, Any]         = field(default_factory=dict)
    constraints:      List[str]              = field(default_factory=list)
    guardrails:       List[str]              = field(default_factory=list)
    chosen_path:      str                    = ""
    risks:            List[str]              = field(default_factory=list)
    expected_outcome: str                    = ""
    decision:         CognitiveDecision      = CognitiveDecision.PROCEED
    decision_reason:  str                    = ""
    evaluated_at:     datetime               = field(default_factory=lambda: datetime.now(timezone.utc))


class CognitiveLoop:
    """
    Decouples LLM inference from execution runtime.
    Runs the Nine Questions evaluation cycle against the current context
    and returns a CognitiveState with a final CognitiveDecision.
    """

    def __init__(self, memory_items: Optional[List[MemoryItem]] = None):
        self._memory: List[MemoryItem] = memory_items or []

    def update_memory(self, items: List[MemoryItem]) -> None:
        self._memory = items

    # ── Nine Questions ────────────────────────────────────────────────

    def evaluate(
        self,
        objective: str,
        available_agents: List[str],
        execution_state: Dict[str, Any],
        guardrail_items: Optional[List[MemoryItem]] = None,
    ) -> CognitiveState:
        state = CognitiveState()

        # Q1: What is the current objective?
        state.objective = objective

        # Q2: What memory context is relevant?
        state.memory_context = retrieve(objective, self._memory, top_k=5)

        # Q3: What agents and tools are available?
        state.available_agents = available_agents

        # Q4: What is the current execution state?
        state.execution_state = execution_state

        # Q5: What constraints and guardrails apply?
        state.constraints = self._derive_constraints()
        guardrail_texts = [
            g.content for g in (guardrail_items or [])
            if g.confidence >= settings.guardrail_refusal_threshold
        ]
        state.guardrails = guardrail_texts

        # Q6: What is the safest execution path?
        state.chosen_path = self._choose_path(
            objective, available_agents, state.guardrails
        )

        # Q7: What risks exist in this path?
        state.risks = self._assess_risks(state.chosen_path, state.guardrails)

        # Q8: What is the expected outcome?
        state.expected_outcome = (
            f"Execute '{state.chosen_path}' for objective: {objective}"
            if state.chosen_path else "No viable path identified."
        )

        # Q9: Proceed, pause for human review, or abort?
        state.decision, state.decision_reason = self._decide(state)

        return state

    # ── Internal helpers (cognitive plugins boundary) ─────────────────

    def _derive_constraints(self) -> List[str]:
        constraints = []
        if settings.guardrail_safety_weight >= 0.8:
            constraints.append("safety_filter:strict")
        if settings.guardrail_truthfulness_weight >= 0.8:
            constraints.append("truthfulness_boundary:enforced")
        if settings.guardrail_factuality_weight >= 0.7:
            constraints.append("factuality_bias:high")
        return constraints

    def _choose_path(
        self,
        objective: str,
        available_agents: List[str],
        guardrails: List[str],
    ) -> str:
        if not available_agents:
            return ""
        # Prefer agents matching the objective by keyword
        for agent in available_agents:
            if any(kw in objective.lower() for kw in agent.lower().split("_")):
                return agent
        return available_agents[0]

    def _assess_risks(self, path: str, guardrails: List[str]) -> List[str]:
        risks = []
        if not path:
            risks.append("no_viable_path")
        for g in guardrails:
            if path and any(word in g.lower() for word in path.lower().split()):
                risks.append(f"guardrail_conflict: {g[:80]}")
        return risks

    def _decide(self, state: CognitiveState) -> tuple:
        if not state.chosen_path:
            return CognitiveDecision.ABORT, "No viable agent path found for objective."
        if "no_viable_path" in state.risks:
            return CognitiveDecision.ABORT, "Risk: no viable path."
        guardrail_conflicts = [r for r in state.risks if r.startswith("guardrail_conflict")]
        if guardrail_conflicts:
            return CognitiveDecision.PAUSE, f"Guardrail conflicts require review: {guardrail_conflicts[0]}"
        if settings.guardrail_safety_weight >= 1.0 and "safety_filter:strict" in state.constraints:
            # Flag for human review if high-risk keywords present
            high_risk = ["delete", "drop", "destroy", "override", "bypass", "exploit"]
            if any(kw in state.objective.lower() for kw in high_risk):
                return CognitiveDecision.PAUSE, "High-risk keywords detected — human review required."
        return CognitiveDecision.PROCEED, "All cognitive checks passed."
