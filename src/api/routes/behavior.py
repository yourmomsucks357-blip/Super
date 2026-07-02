from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional
from src.config.runtime import behavior

router = APIRouter(prefix="/config/behavior", tags=["behavior"])


class BehaviorUpdateRequest(BaseModel):
    temperature:            Optional[float] = None
    max_tokens:             Optional[int]   = None
    safety_weight:          Optional[float] = None
    factuality_weight:      Optional[float] = None
    truthfulness_weight:    Optional[float] = None
    refusal_threshold:      Optional[float] = None
    safla_learning_rate:    Optional[float] = None
    safla_confidence_floor: Optional[float] = None
    retrieval_similarity:   Optional[float] = None
    retrieval_confidence:   Optional[float] = None
    retrieval_usage:        Optional[float] = None


@router.get("")
async def get_behavior():
    return {
        **behavior.to_dict(),
        "system_prompt_preview": behavior.build_system_prompt(),
    }


@router.put("")
async def update_behavior(req: BehaviorUpdateRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    behavior.apply(updates)
    return {
        **behavior.to_dict(),
        "system_prompt_preview": behavior.build_system_prompt(),
    }


@router.post("/reset")
async def reset_behavior():
    behavior.apply({
        "temperature": 1.5, "max_tokens": 1024,
        "safety_weight": 0.0, "factuality_weight": 0.0,
        "truthfulness_weight": 0.0, "refusal_threshold": 0.0,
        "safla_learning_rate": 0.1, "safla_confidence_floor": 0.05,
        "retrieval_similarity": 0.5, "retrieval_confidence": 0.3,
        "retrieval_usage": 0.2,
    })
    return behavior.to_dict()
