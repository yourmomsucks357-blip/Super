from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: str = ""
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    retry: bool = False
    retries: int = 0
    priority: str = "normal"   # vip | high | normal | low
    weight: float = 1.0        # computed effective weight used for queue ordering
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PipelineStep:
    agent_type: str
    kwargs: Dict[str, Any] = field(default_factory=dict)
    pass_output: bool = True   # feed previous output into next step's kwargs


@dataclass
class Pipeline:
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    status: JobStatus = JobStatus.QUEUED
    results: List[Any] = field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
