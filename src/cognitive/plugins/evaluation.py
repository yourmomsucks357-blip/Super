"""
Outcome Evaluator — self-judgment plugin (Success / Failure path).

Implements the self-assessment loop described in the spec:
  - Validates actual output against expected outcome
  - Routes to Success → distill procedural strategy
  - Routes to Failure → extract negative guardrail + run reflection
  - Feeds result back into SAFLA consolidation
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.memory.models import MemoryOutcome, ExperientialStrategy
from src.memory.experiential import ExperientialRepository
from src.memory.safla import update_confidence


@dataclass
class EvaluationResult:
    outcome:          MemoryOutcome
    score:            float = 0.0          # 0–1 quality estimate
    reflection:       str  = ""
    new_strategy_id:  Optional[str] = None
    new_guardrail_ids: List[str] = field(default_factory=list)


class OutcomeEvaluator:
    """
    Self-judgment component of the SAFLA loop.

    Flow:
        Agent Output → judge() → EvaluationResult
                                   ├── SUCCESS → distill_strategy()
                                   └── FAILURE → extract_guardrail() via ExperientialRepository
    """

    def __init__(self, repository: Optional[ExperientialRepository] = None):
        self._repo = repository or ExperientialRepository()

    def judge(
        self,
        objective: str,
        output: Any,
        expected_keywords: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> EvaluationResult:
        """Determine success/failure and score the output."""
        if error:
            return EvaluationResult(
                outcome=MemoryOutcome.FAILURE,
                score=0.0,
                reflection=f"Execution error: {error}",
            )
        if output is None:
            return EvaluationResult(
                outcome=MemoryOutcome.FAILURE,
                score=0.0,
                reflection="No output produced.",
            )
        # Score based on keyword overlap if hints are provided
        score = 1.0
        reflection = "Execution completed successfully."
        if expected_keywords:
            output_text = str(output).lower()
            matched = sum(1 for kw in expected_keywords if kw.lower() in output_text)
            score = matched / len(expected_keywords)
            if score < 0.5:
                return EvaluationResult(
                    outcome=MemoryOutcome.FAILURE,
                    score=score,
                    reflection=f"Output matched only {matched}/{len(expected_keywords)} expected keywords.",
                )
            reflection = f"Output matched {matched}/{len(expected_keywords)} expected keywords."
        return EvaluationResult(
            outcome=MemoryOutcome.SUCCESS,
            score=score,
            reflection=reflection,
        )

    def consolidate(
        self,
        eval_result: EvaluationResult,
        objective: str,
        output_summary: str,
        used_strategy_ids: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """
        Post-judgment SAFLA consolidation step.
        Distills a new strategy or guardrail and updates confidence
        on any strategies used during this task.
        """
        if eval_result.outcome == MemoryOutcome.SUCCESS:
            strategy = self._repo.distill_from_outcome(
                title=f"Strategy: {objective[:60]}",
                description=objective,
                content=output_summary,
                outcome=MemoryOutcome.SUCCESS,
                task_pattern=objective,
            )
            eval_result.new_strategy_id = strategy.item_id
        else:
            # Strip user-specific params → evergreen guardrail
            guardrail = self._repo.distill_from_outcome(
                title=f"Avoid: {objective[:60]}",
                description=eval_result.reflection,
                content=f"Pattern to avoid: {objective}. Reason: {eval_result.reflection}",
                outcome=MemoryOutcome.FAILURE,
                task_pattern=objective,
            )
            eval_result.new_guardrail_ids.append(guardrail.item_id)

        # Apply SAFLA to all strategies used in this task
        if used_strategy_ids:
            new_guardrails = self._repo.record_outcome(
                used_strategy_ids, eval_result.outcome
            )
            eval_result.new_guardrail_ids.extend(new_guardrails)

        return eval_result
