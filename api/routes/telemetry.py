from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

from src.telemetry import collector, tracer

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class EventOut(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    agent_id: Optional[str]
    run_id: Optional[str]
    payload: Dict[str, Any]
    tags: Dict[str, str]


class MetricOut(BaseModel):
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


@router.get("/events", response_model=List[EventOut])
async def get_events(limit: int = Query(100, ge=1, le=1000)):
    events = collector.get_events(limit=limit)
    return [
        EventOut(
            event_id=e.event_id,
            event_type=e.event_type.value,
            timestamp=e.timestamp,
            agent_id=e.agent_id,
            run_id=e.run_id,
            payload=e.payload,
            tags=e.tags,
        )
        for e in events
    ]


@router.get("/metrics", response_model=List[MetricOut])
async def get_metrics(limit: int = Query(100, ge=1, le=1000)):
    metrics = collector.get_metrics(limit=limit)
    return [
        MetricOut(
            name=m.name,
            value=m.value,
            unit=m.unit,
            timestamp=m.timestamp,
            tags=m.tags,
        )
        for m in metrics
    ]


@router.get("/stats")
async def get_stats():
    return collector.stats()


@router.get("/traces/active")
async def get_active_traces():
    spans = tracer.active_spans()
    return [
        {
            "span_id": s.span_id,
            "trace_id": s.trace_id,
            "name": s.name,
            "start_time": s.start_time.isoformat(),
            "tags": s.tags,
        }
        for s in spans
    ]
