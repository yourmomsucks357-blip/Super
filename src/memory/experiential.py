"""
Experiential Memory — ReasoningBank implementation.

Stores strategies as structured triples:
    Title       → strategy name
    Description → contextual scenario
    Content     → step-by-step procedural rules and decision rationales

Extracts strategies from both successful paths AND failed runs.
Failed runs generate evergreen negative guardrail rules via SAFLA.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from .models import ExperientialStrategy, MemoryOutcome, MemoryTier, RetrievalResult
from .retriever import retrieve
from .safla import update_confidence, should_retire, extract_guardrail
from src.config import settings


class ExperientialRepository:
    def __init__(self):
        self._strategies: Dict[str, ExperientialStrategy] = {}

    # ── CRUD ──────────────────────────────────────────────────────────

    def add(self, strategy: ExperientialStrategy) -> ExperientialStrategy:
        strategy.tier = MemoryTier.EXPERIENTIAL
        if strategy.confidence == 0.5:  # default — apply initial setting
            strategy.confidence = settings.safla_initial_confidence
        self._strategies[strategy.item_id] = strategy
        return strategy

    def get(self, item_id: str) -> Optional[ExperientialStrategy]:
        return self._strategies.get(item_id)

    def all(self) -> List[ExperientialStrategy]:
        return list(self._strategies.values())

    def guardrails(self) -> List[ExperientialStrategy]:
        return [s for s in self._strategies.values() if s.is_guardrail]

    def positive_strategies(self) -> List[ExperientialStrategy]:
        return [s for s in self._strategies.values() if not s.is_guardrail]

    # ── SAFLA feedback ────────────────────────────────────────────────

    def record_outcome(
        self,
        strategy_ids: List[str],
        outcome: MemoryOutcome,
    ) -> List[str]:
        """
        Apply SAFLA confidence update to each strategy used in a task.
        On failure: extract a guardrail from each failing strategy.
        Returns list of newly created guardrail IDs (if any).
        """
        new_guardrail_ids: List[str] = []
        for sid in strategy_ids:
            strategy = self._strategies.get(sid)
            if not strategy:
                continue
            update_confidence(strategy, outcome)
            if outcome == MemoryOutcome.FAILURE and not strategy.is_guardrail:
                guardrail = extract_guardrail(strategy)
                self._strategies[guardrail.item_id] = guardrail
                new_guardrail_ids.append(guardrail.item_id)
            if should_retire(strategy):
                strategy.metadata["retired"] = True
        return new_guardrail_ids

    def consolidate(self) -> int:
        """Remove strategies below the consolidation threshold. Returns count removed."""
        to_remove = [
            sid for sid, s in self._strategies.items()
            if s.confidence < settings.memory_consolidation_threshold
        ]
        for sid in to_remove:
            del self._strategies[sid]
        return len(to_remove)

    # ── Retrieval ─────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        results = retrieve(query, self.all(), top_k=top_k)  # type: ignore[arg-type]
        for r in results:
            r.item.usage_count += 1
        return results

    def retrieve_guardrails(self, query: str, top_k: int = 3) -> List[RetrievalResult]:
        results = retrieve(query, self.guardrails(), top_k=top_k)  # type: ignore[arg-type]
        return results

    # ── Distillation ──────────────────────────────────────────────────

    def distill_from_outcome(
        self,
        title: str,
        description: str,
        content: str,
        outcome: MemoryOutcome,
        task_pattern: str = "",
        tags: List[str] = [],
    ) -> ExperientialStrategy:
        """
        Create and store a new strategy distilled from a task outcome.
        Success → positive procedural strategy.
        Failure → negative guardrail rule.
        """
        strategy = ExperientialStrategy(
            title=title,
            description=description,
            content=content,
            outcome=outcome,
            is_guardrail=(outcome == MemoryOutcome.FAILURE),
            task_pattern=task_pattern,
            tags=tags,
            confidence=settings.safla_initial_confidence,
        )
        return self.add(strategy)
