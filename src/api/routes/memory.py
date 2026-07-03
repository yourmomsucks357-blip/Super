from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from src.memory.models import MemoryTier, MemoryOutcome
from src.memory.models import MemoryItem, ExperientialStrategy
from src.memory.safla import update_confidence, should_retire
from src.memory.store import (
    associative_store  as _associative,
    temporal_store     as _temporal,
    experiential_store as _experiential,
    working_store      as _working,
)

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryAddRequest(BaseModel):
    tier:    str
    title:   str
    content: str
    tags:    List[str] = []
    metadata: Dict[str, Any] = {}


class StrategyRequest(BaseModel):
    title:       str
    description: str
    content:     str
    outcome:     str = "success"   # success | failure
    task_pattern: str = ""
    tags:        List[str] = []


class SAFLAFeedbackRequest(BaseModel):
    item_id: str
    outcome: str  # success | failure


# ── Overview ─────────────────────────────────────────────────────────────────

@router.get("")
async def memory_overview():
    return {
        "associative":  {"count": len(_associative.all())},
        "temporal":     {"count": len(_temporal.all())},
        "experiential": {
            "count":      len(_experiential.all()),
            "guardrails": len(_experiential.guardrails()),
            "strategies": len(_experiential.positive_strategies()),
        },
        "working": {
            "count":       len(_working.all()),
            "utilization": _working.utilization,
            "subgoals":    len(_working.subgoal_tree()),
        },
    }


# ── Associative ───────────────────────────────────────────────────────────────

@router.get("/associative")
async def list_associative(query: str = "", top_k: int = 20):
    if query:
        results = _associative.retrieve(query, top_k=top_k)
        return [{"item": _fmt(r.item), "score": r.relevance_score} for r in results]
    return [_fmt(i) for i in _associative.all()]


@router.post("/associative")
async def add_associative(req: MemoryAddRequest):
    item = MemoryItem(title=req.title, content=req.content, tags=req.tags, metadata=req.metadata)
    _associative.add(item)
    return _fmt(item)


# ── Temporal ──────────────────────────────────────────────────────────────────

@router.get("/temporal")
async def list_temporal():
    return [_fmt(i) for i in _temporal.timeline()]


@router.post("/temporal")
async def add_temporal(req: MemoryAddRequest, follows_id: Optional[str] = None):
    item = MemoryItem(title=req.title, content=req.content, tags=req.tags)
    _temporal.add_event(item, follows_id=follows_id)
    return _fmt(item)


# ── Experiential ──────────────────────────────────────────────────────────────

@router.get("/experiential")
async def list_experiential(guardrails_only: bool = False, query: str = "", top_k: int = 20):
    if query:
        fn = _experiential.retrieve_guardrails if guardrails_only else _experiential.retrieve
        results = fn(query, top_k=top_k)
        return [{"item": _fmt(r.item), "score": r.relevance_score} for r in results]
    items = _experiential.guardrails() if guardrails_only else _experiential.all()
    return [_fmt(i) for i in items]


@router.post("/experiential")
async def add_strategy(req: StrategyRequest):
    strategy = _experiential.distill_from_outcome(
        title=req.title,
        description=req.description,
        content=req.content,
        outcome=MemoryOutcome(req.outcome),
        task_pattern=req.task_pattern,
        tags=req.tags,
    )
    return _fmt(strategy)


@router.post("/experiential/safla")
async def safla_feedback(req: SAFLAFeedbackRequest):
    strategy = _experiential.get(req.item_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    update_confidence(strategy, MemoryOutcome(req.outcome))
    retired = should_retire(strategy)
    return {"item_id": req.item_id, "confidence": strategy.confidence, "retired": retired}


@router.post("/experiential/consolidate")
async def consolidate():
    removed = _experiential.consolidate()
    return {"removed": removed, "remaining": len(_experiential.all())}


# ── Working context ───────────────────────────────────────────────────────────

@router.get("/working")
async def list_working():
    return {
        "items": [_fmt(i) for i in _working.all()],
        "subgoals": _working.subgoal_tree(),
        "utilization": _working.utilization,
    }


@router.delete("/working")
async def clear_working():
    _working.clear()
    return {"cleared": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(item: MemoryItem) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "item_id":    item.item_id,
        "tier":       item.tier.value,
        "title":      item.title,
        "content":    item.content,
        "tags":       item.tags,
        "confidence": item.confidence,
        "usage_count": item.usage_count,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }
    if isinstance(item, ExperientialStrategy):
        d.update({
            "description":  item.description,
            "outcome":      item.outcome.value,
            "kind":         item.kind,
            "is_guardrail": item.is_guardrail,
            "task_pattern": item.task_pattern,
        })
    return d
