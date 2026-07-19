import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Callable, Deque, List, Optional

from .models import EventType, Metric, TelemetryEvent
from src.config import settings

logger = logging.getLogger(__name__)


class TelemetryCollector:
    def __init__(self):
        self._buffer: Deque[TelemetryEvent] = deque(maxlen=settings.max_telemetry_buffer)
        self._metrics: Deque[Metric] = deque(maxlen=settings.max_telemetry_buffer)
        self._handlers: List[Callable[[TelemetryEvent], None]] = []
        self._flush_task: Optional[asyncio.Task] = None

    def add_handler(self, handler: Callable[[TelemetryEvent], None]) -> None:
        self._handlers.append(handler)

    def emit(self, event: TelemetryEvent) -> None:
        if not settings.telemetry_enabled:
            return
        self._buffer.append(event)
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.warning(f"Telemetry handler error: {exc}")

    def record_metric(self, metric: Metric) -> None:
        self._metrics.append(metric)
        self.emit(TelemetryEvent(
            event_type=EventType.METRIC,
            payload={"name": metric.name, "value": metric.value, "unit": metric.unit},
            tags=metric.tags,
        ))

    def agent_start(self, agent_id: str, run_id: str, agent_type: str) -> None:
        self.emit(TelemetryEvent(
            event_type=EventType.AGENT_START,
            agent_id=agent_id,
            run_id=run_id,
            payload={"agent_type": agent_type},
        ))

    def agent_complete(self, agent_id: str, run_id: str, duration_ms: float) -> None:
        self.emit(TelemetryEvent(
            event_type=EventType.AGENT_COMPLETE,
            agent_id=agent_id,
            run_id=run_id,
            payload={"duration_ms": duration_ms},
        ))
        self.record_metric(Metric(
            name="agent.duration_ms",
            value=duration_ms,
            unit="ms",
            tags={"agent_id": agent_id},
        ))

    def agent_failed(self, agent_id: str, run_id: str, error: str) -> None:
        self.emit(TelemetryEvent(
            event_type=EventType.AGENT_FAILED,
            agent_id=agent_id,
            run_id=run_id,
            payload={"error": error},
        ))

    def emit_raw(self, event_type_str: str, payload: dict) -> None:
        """Emit a free-form event by string name (used by job queue etc.)."""
        self.emit(TelemetryEvent(
            event_type=EventType.LOG,
            payload={"event": event_type_str, **payload},
        ))

    def get_events(self, limit: int = 100) -> List[TelemetryEvent]:
        events = list(self._buffer)
        return events[-limit:]

    def get_metrics(self, limit: int = 100) -> List[Metric]:
        metrics = list(self._metrics)
        return metrics[-limit:]

    def stats(self) -> dict:
        events = list(self._buffer)
        by_type: dict = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        return {
            "total_events": len(events),
            "total_metrics": len(self._metrics),
            "by_type": by_type,
            "buffer_capacity": settings.max_telemetry_buffer,
        }

    async def start(self) -> None:
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(settings.telemetry_flush_interval)
            logger.debug(f"Telemetry flush: {self.stats()}")


collector = TelemetryCollector()
