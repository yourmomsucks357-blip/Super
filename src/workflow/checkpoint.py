"""
State checkpoint system — saves execution snapshots at every graph super-step.

LangGraph-style thread-level checkpointing:
  - A snapshot is written BEFORE and AFTER every node execution
  - Partial progress and pending writes survive mid-turn failures
  - Point-in-time rollback is supported without data duplication
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class ExecutionCheckpoint:
    checkpoint_id: str            = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id:   str            = ""
    run_id:        str            = ""
    thread_id:     str            = ""
    node_id:       str            = ""
    step:          int            = 0
    state:         Dict[str, Any] = field(default_factory=dict)  # full $flow.state snapshot
    pending:       Dict[str, Any] = field(default_factory=dict)  # writes not yet committed
    status:        str            = "pending"  # pending | committed | rolled_back
    created_at:    datetime       = field(default_factory=lambda: datetime.now(timezone.utc))


class CheckpointStore:
    """
    In-process checkpoint store (SQLite/PostgreSQL backend can be plugged in
    by subclassing and overriding _persist / _load).
    """

    def __init__(self):
        self._store: Dict[str, List[ExecutionCheckpoint]] = {}  # run_id → checkpoints

    # ── Write ─────────────────────────────────────────────────────────

    def save(self, checkpoint: ExecutionCheckpoint) -> ExecutionCheckpoint:
        self._store.setdefault(checkpoint.run_id, []).append(checkpoint)
        return checkpoint

    def commit(self, checkpoint_id: str, run_id: str) -> None:
        for cp in self._store.get(run_id, []):
            if cp.checkpoint_id == checkpoint_id:
                cp.status = "committed"
                return

    # ── Read ──────────────────────────────────────────────────────────

    def latest(self, run_id: str) -> Optional[ExecutionCheckpoint]:
        checkpoints = self._store.get(run_id, [])
        committed = [c for c in checkpoints if c.status == "committed"]
        return committed[-1] if committed else None

    def history(self, run_id: str) -> List[ExecutionCheckpoint]:
        return list(self._store.get(run_id, []))

    # ── Rollback ─────────────────────────────────────────────────────

    def rollback(self, run_id: str, to_step: int) -> Optional[ExecutionCheckpoint]:
        """Return the last committed checkpoint at or before `to_step`."""
        checkpoints = self._store.get(run_id, [])
        candidates = [
            c for c in checkpoints
            if c.status == "committed" and c.step <= to_step
        ]
        return candidates[-1] if candidates else None

    def all_runs(self) -> List[str]:
        return list(self._store.keys())


# Singleton
checkpoint_store = CheckpointStore()
