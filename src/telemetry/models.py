from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class EventType(str, Enum):
    AGENT_START = "agent.start"
    AGENT_COMPLETE = "agent.complete"
    AGENT_FAILED = "agent.failed"
    AGENT_TIMEOUT = "agent.timeout"
    AGENT_CANCELLED = "agent.cancelled"
    METRIC = "metric"
    LOG = "log"
    TRACE_START = "trace.start"
    TRACE_END = "trace.end"


@dataclass
class TelemetryEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.LOG
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Span:
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    parent_span_id: Optional[str] = None

    def finish(self) -> None:
        self.end_time = datetime.now(timezone.utc)
        if self.start_time:
            delta = (self.end_time - self.start_time).total_seconds() * 1000
            self.duration_ms = delta
