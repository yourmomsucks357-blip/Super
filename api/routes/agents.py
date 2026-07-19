from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.agents import AgentContext, AgentResult, executor, registry

router = APIRouter(prefix="/agents", tags=["agents"])


class RunRequest(BaseModel):
    agent_type: str
    kwargs: Dict[str, Any] = {}
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = {}
    retry: bool = False
    retries: Optional[int] = None


class RunResponse(BaseModel):
    run_id: str
    agent_id: str
    status: str
    output: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@router.get("/types", response_model=List[str])
async def list_agent_types():
    return registry.list_types()


@router.post("/run", response_model=RunResponse)
async def run_agent(req: RunRequest):
    try:
        agent = registry.create(req.agent_type)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    context = AgentContext(
        agent_id=agent.agent_id,
        metadata=req.metadata,
    )

    if req.retry:
        result: AgentResult = await executor.run_with_retry(
            agent, context, retries=req.retries, **req.kwargs
        )
    else:
        result = await executor.run(agent, context, timeout=req.timeout, **req.kwargs)

    return RunResponse(
        run_id=result.run_id,
        agent_id=result.agent_id,
        status=result.status.value,
        output=result.output,
        error=result.error,
        duration_ms=result.duration_ms,
    )


@router.delete("/run/{run_id}")
async def cancel_run(run_id: str):
    cancelled = await executor.cancel(run_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Run not found or already completed")
    return {"cancelled": True, "run_id": run_id}
