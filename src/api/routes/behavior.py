from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional
from src.config.runtime import behavior, _DEFAULT_BEHAVIOR

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
    behavior.apply(_DEFAULT_BEHAVIOR)
    return behavior.to_dict()
