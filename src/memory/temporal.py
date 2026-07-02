"""
Temporal Knowledge Graph — directed graph capturing sequential events.

Tracks user traits, behavioral trends, and chronologies.
Edge weights decay with time and strengthen with interaction frequency.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from .models import MemoryItem, MemoryTier, TemporalEdge, RetrievalResult
from .retriever import retrieve
import math


_DECAY_HALF_LIFE_DAYS = 30.0


def _time_decay(last_updated: datetime) -> float:
    """Exponential decay: weight halves every DECAY_HALF_LIFE_DAYS days."""
    delta = (datetime.now(timezone.utc) - last_updated).total_seconds()
    days = delta / 86400.0
    return math.exp(-math.log(2) * days / _DECAY_HALF_LIFE_DAYS)


class TemporalKnowledgeGraph:
    def __init__(self):
        self._nodes: Dict[str, MemoryItem] = {}
        self._edges: List[TemporalEdge] = []

    # ── Nodes ─────────────────────────────────────────────────────────

    def add_event(self, item: MemoryItem, follows_id: Optional[str] = None) -> MemoryItem:
        item.tier = MemoryTier.TEMPORAL
        self._nodes[item.item_id] = item
        if follows_id and follows_id in self._nodes:
            self._edges.append(TemporalEdge(
                source_id=follows_id,
                target_id=item.item_id,
                relation="precedes",
                weight=1.0,
            ))
        return item

    def all(self) -> List[MemoryItem]:
        return list(self._nodes.values())

    # ── Edges ─────────────────────────────────────────────────────────

    def get_edges(self, node_id: str) -> List[TemporalEdge]:
        return [e for e in self._edges if e.source_id == node_id]

    def reinforce_edge(self, source_id: str, target_id: str, delta: float = 0.1) -> None:
        for edge in self._edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                edge.weight = min(1.0, edge.weight + delta)
                edge.last_updated = datetime.now(timezone.utc)

    def decay_all_edges(self) -> None:
        """Apply time-based decay to all edge weights."""
        for edge in self._edges:
            edge.weight *= _time_decay(edge.last_updated)

    # ── Retrieval ─────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        return retrieve(query, self.all(), top_k=top_k)

    # ── Timeline ─────────────────────────────────────────────────────

    def timeline(self) -> List[MemoryItem]:
        return sorted(self._nodes.values(), key=lambda n: n.created_at)
