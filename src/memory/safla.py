"""
Self-Aware Feedback Loop Algorithm (SAFLA).

Confidence update rule:
    c_{t+1} = c_t + α * r_t

where:
    α   = safla_learning_rate
    r_t = +1.0 on success, -1.0 on failure

Strategies whose confidence falls to or below safla_confidence_floor
are flagged for retirement (guardrail extraction or discard).
"""
from datetime import datetime, timezone
from typing import List

from .models import ExperientialStrategy, MemoryItem, MemoryOutcome
from src.config import settings


def update_confidence(item: MemoryItem, outcome: MemoryOutcome) -> MemoryItem:
    """Apply one SAFLA feedback step to a memory item."""
    r = 1.0 if outcome == MemoryOutcome.SUCCESS else -1.0
    new_c = item.confidence + settings.safla_learning_rate * r
    item.confidence = max(
        settings.safla_confidence_floor,
        min(settings.safla_confidence_ceiling, new_c),
    )
    item.updated_at = datetime.now(timezone.utc)
    return item


def should_retire(item: MemoryItem) -> bool:
    """Return True when a strategy's confidence has decayed to the floor."""
    return item.confidence <= settings.safla_confidence_floor


def batch_update(items: List[MemoryItem], outcome: MemoryOutcome) -> List[MemoryItem]:
    return [update_confidence(i, outcome) for i in items]


def extract_guardrail(strategy: ExperientialStrategy) -> ExperientialStrategy:
    """
    Convert a failed strategy into an evergreen negative guardrail.
    Strips user-specific parameters to isolate the underlying failure pattern.
    """
    guardrail = ExperientialStrategy(
        title=f"[GUARDRAIL] {strategy.title}",
        description=strategy.description,
        content=f"Avoid: {strategy.content}",
        tags=strategy.tags + ["guardrail"],
        confidence=settings.safla_initial_confidence,
        outcome=MemoryOutcome.GUARDRAIL,
        kind="guardrail",
        is_guardrail=True,
        task_pattern=strategy.task_pattern or strategy.title,
        metadata={**strategy.metadata, "source_outcome": MemoryOutcome.FAILURE.value},
    )
    return guardrail
