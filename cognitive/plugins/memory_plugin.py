"""
Memory Plugin — internal cognitive plugin for memory retrieval.

Bridges the cognitive loop to the 4-tier memory system.
Does NOT import from external execution tools.
"""
from typing import List, Optional
from src.memory.models import MemoryItem, RetrievalResult
from src.memory.retriever import retrieve
from src.memory.associative import AssociativeMemory
from src.memory.temporal import TemporalKnowledgeGraph
from src.memory.experiential import ExperientialRepository
from src.memory.working import WorkingContextMemory


class MemoryPlugin:
    """
    Unified retrieval interface for all memory tiers.
    The cognitive loop calls this plugin; the plugin coordinates
    across the four backends without exposing raw stores upward.
    """

    def __init__(
        self,
        associative: Optional[AssociativeMemory] = None,
        temporal: Optional[TemporalKnowledgeGraph] = None,
        experiential: Optional[ExperientialRepository] = None,
        working: Optional[WorkingContextMemory] = None,
    ):
        self.associative   = associative   or AssociativeMemory()
        self.temporal      = temporal      or TemporalKnowledgeGraph()
        self.experiential  = experiential  or ExperientialRepository()
        self.working       = working       or WorkingContextMemory()

    def retrieve_all(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Retrieve from all tiers, merge, and re-rank."""
        all_items: List[MemoryItem] = (
            self.associative.all()
            + self.temporal.all()
            + list(self.experiential.all())
            + self.working.all()
        )
        return retrieve(query, all_items, top_k=top_k)

    def retrieve_strategies(self, query: str, top_k: int = 3) -> List[RetrievalResult]:
        return self.experiential.retrieve(query, top_k=top_k)

    def retrieve_guardrails(self, query: str, top_k: int = 3) -> List[RetrievalResult]:
        return self.experiential.retrieve_guardrails(query, top_k=top_k)

    def working_context(self) -> List[MemoryItem]:
        return self.working.all()

    def pending_subgoals(self):
        return self.working.pending_subgoals()
