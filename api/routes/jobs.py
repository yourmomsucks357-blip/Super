from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.jobs.models import Job, JobStatus, Pipeline, PipelineStep
from src.jobs.queue import job_queue, AGENT_TYPE_WEIGHTS


class JobRequest(BaseModel):
    agent_type: str
    kwargs: Dict[str, Any] = {}
    priority: str = "normal"
    retry: bool = False
    retries: int = 0
    tags: Dict[str, str] = {}


class PipelineRequest(BaseModel):
    name: str = ""
    steps: List[Dict[str, Any]]


class WeightUpdate(BaseModel):
    agent_type: str
    weight: float


router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── Weight management (must come before /{job_id}) ───────────────────────────

@router.get("/weights")
async def get_weights():
    return AGENT_TYPE_WEIGHTS


@router.put("/weights")
async def update_weight(update: WeightUpdate):
    if update.weight <= 0:
        raise HTTPException(status_code=400, detail="Weight must be > 0")
    AGENT_TYPE_WEIGHTS[update.agent_type] = update.weight
    return {"agent_type": update.agent_type, "weight": update.weight}


# ── Pipeline routes (must come before /{job_id}) ─────────────────────────────

@router.post("/pipelines", status_code=201)
async def enqueue_pipeline(req: PipelineRequest):
    steps = [
        PipelineStep(
            agent_type=s["agent_type"],
            kwargs=s.get("kwargs", {}),
            pass_output=s.get("pass_output", True),
        )
        for s in req.steps
    ]
    pipeline = Pipeline(name=req.name, steps=steps)
    job_queue.enqueue_pipeline(pipeline)
    return {"pipeline_id": pipeline.pipeline_id, "steps": len(steps), "status": pipeline.status}


@router.get("/pipelines")
async def list_pipelines(limit: int = Query(20, ge=1, le=100)):
    return [
        {
            "pipeline_id": p.pipeline_id, "name": p.name,
            "status": p.status, "steps": len(p.steps),
            "results": len(p.results), "error": p.error,
            "created_at": p.created_at.isoformat(),
        }
        for p in job_queue.list_pipelines(limit=limit)
    ]


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    p = job_queue.get_pipeline(pipeline_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {
        "pipeline_id": p.pipeline_id, "name": p.name, "status": p.status,
        "steps": [{"agent_type": s.agent_type, "kwargs": s.kwargs} for s in p.steps],
        "results": p.results, "error": p.error,
    }


class JobRequest(BaseModel):
    agent_type: str
    kwargs: Dict[str, Any] = {}
    priority: str = "normal"   # vip | high | normal | low
    retry: bool = False
    retries: int = 0
    tags: Dict[str, str] = {}


class PipelineRequest(BaseModel):
    name: str = ""
    steps: List[Dict[str, Any]]   # [{agent_type, kwargs, pass_output}]


class WeightUpdate(BaseModel):
    agent_type: str
    weight: float


@router.post("", status_code=201)
async def enqueue_job(req: JobRequest):
    job = Job(
        agent_type=req.agent_type,
        kwargs=req.kwargs,
        priority=req.priority,
        retry=req.retry,
        retries=req.retries,
        tags=req.tags,
    )
    job_queue.enqueue(job)
    return {"job_id": job.job_id, "status": job.status, "weight": job.weight}


@router.get("")
async def list_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    status_filter = JobStatus(status) if status else None
    jobs = job_queue.list_jobs(status=status_filter, limit=limit)
    return [
        {
            "job_id": j.job_id, "agent_type": j.agent_type,
            "status": j.status, "priority": j.priority,
            "weight": j.weight, "duration_ms": j.duration_ms,
            "error": j.error, "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id, "agent_type": job.agent_type,
        "status": job.status, "priority": job.priority,
        "weight": job.weight, "result": job.result,
        "error": job.error, "duration_ms": job.duration_ms,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.delete("/{job_id}")
async def cancel_job(job_id: str):
    cancelled = job_queue.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return {"cancelled": job_id}
