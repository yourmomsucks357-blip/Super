from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MemoryTier(str, Enum):
    ASSOCIATIVE  = "associative"   # A-Mem: graph-based nodes, semantic tags, Zettelkasten
    TEMPORAL     = "temporal"      # Temporal KG: sequential events, edge weights
    EXPERIENTIAL = "experiential"  # ReasoningBank: strategies + guardrails from outcomes
    WORKING      = "working"       # Working context: active task state, subgoal trees


class MemoryOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    GUARDRAIL = "guardrail"


@dataclass
class MemoryItem:
    """Base unit for all memory tiers."""
    item_id:    str            = field(default_factory=lambda: str(uuid.uuid4()))
    tier:       MemoryTier     = MemoryTier.WORKING
    title:      str            = ""
    content:    str            = ""
    tags:       List[str]      = field(default_factory=list)
    confidence: float          = 0.5   # SAFLA confidence score (0–1)
    usage_count: int           = 0
    created_at: datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata:   Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperientialStrategy(MemoryItem):
    """
    ReasoningBank entry — Title + Description + Procedural Content.
    Extracted from both successful paths and failure counterfactuals.
    """
    tier:         MemoryTier    = field(default=MemoryTier.EXPERIENTIAL)
    description:  str           = ""    # contextual scenario
    outcome:      MemoryOutcome = MemoryOutcome.SUCCESS
    kind:         str           = "strategy"  # strategy | guardrail
    is_guardrail: bool          = False # True = extracted from failure path
    task_pattern: str           = ""    # user-stripped generalised failure pattern


@dataclass
class TemporalEdge:
    """Weighted directed edge in the temporal knowledge graph."""
    source_id:    str      = ""
    target_id:    str      = ""
    relation:     str      = ""
    weight:       float    = 1.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RetrievalResult:
    """Scored output from the memory retriever."""
    item:                    MemoryItem
    relevance_score:         float = 0.0
    similarity:              float = 0.0
    confidence_contribution: float = 0.0
    usage_contribution:      float = 0.0
