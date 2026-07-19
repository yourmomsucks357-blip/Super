from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class AgentContext:
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_run_id: Optional[str] = None


@dataclass
class AgentResult:
    run_id: str
    agent_id: str
    status: AgentStatus
    output: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(self, agent_id: Optional[str] = None, name: Optional[str] = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name or self.__class__.__name__

    @property
    def agent_type(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def execute(self, context: AgentContext, **kwargs) -> Any:
        """Execute the agent logic. Return the output."""

    async def on_start(self, context: AgentContext) -> None:
        """Hook called before execute."""

    async def on_complete(self, context: AgentContext, result: AgentResult) -> None:
        """Hook called after execute succeeds."""

    async def on_error(self, context: AgentContext, exc: Exception) -> None:
        """Hook called when execute raises."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, name={self.name})"
