"""
Associative Memory (A-Mem) — graph-based, Zettelkasten-inspired.

Each node is a MemoryItem enriched with keywords, metadata tags, and
contextual relationships. New nodes retroactively rewire existing links
based on semantic overlap, mimicking the A-Mem self-wiring mechanism.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from .models import MemoryItem, MemoryTier, RetrievalResult
from .retriever import retrieve


class AssociativeMemory:
    def __init__(self):
        self._nodes: Dict[str, MemoryItem] = {}
        # adjacency: item_id → set of (related_id, relation_label)
        self._edges: Dict[str, List[Tuple[str, str]]] = {}

    # ── Node operations ──────────────────────────────────────────────

    def add(self, item: MemoryItem) -> MemoryItem:
        item.tier = MemoryTier.ASSOCIATIVE
        self._nodes[item.item_id] = item
        self._edges.setdefault(item.item_id, [])
        self._auto_wire(item)
        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        return self._nodes.get(item_id)

    def all(self) -> List[MemoryItem]:
        return list(self._nodes.values())

    def remove(self, item_id: str) -> None:
        self._nodes.pop(item_id, None)
        self._edges.pop(item_id, None)
        for edges in self._edges.values():
            edges[:] = [(rid, rel) for rid, rel in edges if rid != item_id]

    # ── Link operations ───────────────────────────────────────────────

    def link(self, source_id: str, target_id: str, relation: str = "related") -> None:
        if source_id in self._nodes and target_id in self._nodes:
            self._edges[source_id].append((target_id, relation))

    def neighbors(self, item_id: str) -> List[Tuple[MemoryItem, str]]:
        return [
            (self._nodes[rid], rel)
            for rid, rel in self._edges.get(item_id, [])
            if rid in self._nodes
        ]

    # ── Retrieval ─────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        results = retrieve(query, self.all(), top_k=top_k)
        for r in results:
            r.item.usage_count += 1
            r.item.updated_at = datetime.now(timezone.utc)
        return results

    # ── Auto-wiring (retroactive Zettelkasten rewiring) ───────────────

    def _auto_wire(self, new_item: MemoryItem, threshold: float = 0.2) -> None:
        query = new_item.content + " " + " ".join(new_item.tags)
        candidates = [n for n in self._nodes.values() if n.item_id != new_item.item_id]
        if not candidates:
            return
        from .retriever import score_item
        max_u = max((c.usage_count for c in candidates), default=1) or 1
        for node in candidates:
            result = score_item(query, node, max_u)
            if result.similarity >= threshold:
                self.link(new_item.item_id, node.item_id, "semantic_link")
