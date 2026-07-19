"""
Working Context Memory — temporary state for the active task.

Holds structured text, latent state references, subgoal trees, and
immediate execution context. Enforces a maximum slot limit defined
by memory_max_working_context. Oldest items are evicted first.
"""
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from .models import MemoryItem, MemoryTier
from src.config import settings


class WorkingContextMemory:
    def __init__(self):
        self._slots: OrderedDict[str, MemoryItem] = OrderedDict()
        self._subgoals: List[Dict[str, Any]] = []

    # ── Context slots ─────────────────────────────────────────────────

    def set(self, item: MemoryItem) -> MemoryItem:
        item.tier = MemoryTier.WORKING
        if item.item_id in self._slots:
            self._slots.move_to_end(item.item_id)
        self._slots[item.item_id] = item
        self._evict_if_full()
        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        return self._slots.get(item_id)

    def all(self) -> List[MemoryItem]:
        return list(self._slots.values())

    def clear(self) -> None:
        self._slots.clear()
        self._subgoals.clear()

    # ── Subgoal tree ──────────────────────────────────────────────────

    def push_subgoal(self, goal: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._subgoals.append({
            "goal": goal,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        })

    def complete_subgoal(self, goal: str) -> None:
        for sg in self._subgoals:
            if sg["goal"] == goal and sg["status"] == "pending":
                sg["status"] = "completed"
                break

    def pending_subgoals(self) -> List[Dict[str, Any]]:
        return [sg for sg in self._subgoals if sg["status"] == "pending"]

    def subgoal_tree(self) -> List[Dict[str, Any]]:
        return list(self._subgoals)

    # ── Eviction ──────────────────────────────────────────────────────

    def _evict_if_full(self) -> None:
        while len(self._slots) > settings.memory_max_working_context:
            self._slots.popitem(last=False)  # evict oldest

    @property
    def utilization(self) -> float:
        return len(self._slots) / settings.memory_max_working_context
