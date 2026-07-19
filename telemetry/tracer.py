import contextlib
from datetime import datetime
from typing import Dict, Optional

from .models import Span
from .collector import collector
from .models import EventType, TelemetryEvent


class Tracer:
    def __init__(self):
        self._active_spans: Dict[str, Span] = {}

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Span:
        span = Span(name=name, tags=tags or {}, parent_span_id=parent_span_id)
        if trace_id:
            span.trace_id = trace_id
        self._active_spans[span.span_id] = span
        collector.emit(TelemetryEvent(
            event_type=EventType.TRACE_START,
            payload={"span_id": span.span_id, "trace_id": span.trace_id, "name": name},
            tags=tags or {},
        ))
        return span

    def finish_span(self, span: Span) -> Span:
        span.finish()
        self._active_spans.pop(span.span_id, None)
        collector.emit(TelemetryEvent(
            event_type=EventType.TRACE_END,
            payload={
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "name": span.name,
                "duration_ms": span.duration_ms,
            },
            tags=span.tags,
        ))
        return span

    @contextlib.asynccontextmanager
    async def trace(self, name: str, **tags):
        span = self.start_span(name, tags={k: str(v) for k, v in tags.items()})
        try:
            yield span
        finally:
            self.finish_span(span)

    def active_spans(self) -> list:
        return list(self._active_spans.values())


tracer = Tracer()
