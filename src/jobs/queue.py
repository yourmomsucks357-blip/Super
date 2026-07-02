import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import Job, JobStatus, Pipeline, PipelineStep
from src.agents import executor, registry, AgentContext
from src.agents.base import AgentStatus
from src.config import settings
from src.telemetry import collector


# Per-agent-type concurrency weight: fraction of max_concurrent_agents slots reserved
# Values > 1.0 mean the type can use more than its fair share; < 1.0 means restricted
AGENT_TYPE_WEIGHTS: Dict[str, float] = {
    "echo":      1.0,
    "compute":   2.0,   # compute-heavy, more slots
    "sleep":     0.5,   # low priority, fewer slots
    "assistant": 1.5,
    "router":    1.5,
}


_PRIORITY_BOOST: Dict[str, float] = {
    "vip":    settings.priority_boost_vip,
    "high":   settings.priority_boost_high,
    "normal": settings.priority_boost_normal,
    "low":    settings.priority_boost_low,
}
_DECAY: float = settings.weight_decay


def _effective_weight(job: Job, attempt: int = 0) -> float:
    """Compute scheduling weight. Higher = executed sooner."""
    boost       = _PRIORITY_BOOST.get(job.priority, 1.0)
    type_weight = AGENT_TYPE_WEIGHTS.get(job.agent_type, 1.0)
    decay       = _DECAY ** attempt
    return job.weight * boost * type_weight * decay


class JobQueue:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._pipelines: Dict[str, Pipeline] = {}
        self._worker_task: Optional[asyncio.Task] = None

    # ── Job management ──────────────────────────────────────────────

    def enqueue(self, job: Job) -> Job:
        job.weight = _effective_weight(job)
        self._jobs[job.job_id] = job
        priority_score = -job.weight   # negate so higher weight = dequeued first
        self._queue.put_nowait((priority_score, job.created_at.timestamp(), job.job_id))
        collector.emit_raw("job.queued", {"job_id": job.job_id, "weight": job.weight,
                                           "priority": job.priority, "agent_type": job.agent_type})
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Job]:
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
            return True
        return False

    # ── Pipeline management ─────────────────────────────────────────

    def enqueue_pipeline(self, pipeline: Pipeline) -> Pipeline:
        self._pipelines[pipeline.pipeline_id] = pipeline
        asyncio.create_task(self._run_pipeline(pipeline))
        return pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self, limit: int = 50) -> List[Pipeline]:
        return sorted(self._pipelines.values(), key=lambda p: p.created_at, reverse=True)[:limit]

    # ── Worker ──────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()

    async def _worker_loop(self) -> None:
        while True:
            _, _, job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            if not job or job.status == JobStatus.CANCELLED:
                self._queue.task_done()
                continue
            asyncio.create_task(self._execute_job(job))
            self._queue.task_done()

    async def _execute_job(self, job: Job) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        try:
            agent = registry.create(job.agent_type)
            ctx = AgentContext(agent_id=agent.agent_id)
            ctx.metadata["job_id"] = job.job_id

            if job.retry:
                result = await executor.run_with_retry(agent, ctx,
                                                       retries=job.retries, **job.kwargs)
            else:
                result = await executor.run(agent, ctx, **job.kwargs)

            job.result = result.output
            job.error = result.error
            job.duration_ms = result.duration_ms
            job.status = (JobStatus.COMPLETED if result.status == AgentStatus.COMPLETED
                          else JobStatus.FAILED)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        finally:
            job.completed_at = datetime.now(timezone.utc)
            collector.emit_raw(f"job.{job.status.value}",
                               {"job_id": job.job_id, "duration_ms": job.duration_ms})

    async def _run_pipeline(self, pipeline: Pipeline) -> None:
        pipeline.status = JobStatus.RUNNING
        previous_output = None

        for i, step in enumerate(pipeline.steps):
            try:
                agent = registry.create(step.agent_type)
                ctx = AgentContext(agent_id=agent.agent_id)
                ctx.metadata["pipeline_id"] = pipeline.pipeline_id
                ctx.metadata["step"] = i

                kwargs = dict(step.kwargs)
                if step.pass_output and previous_output is not None:
                    kwargs["previous_output"] = previous_output

                result = await executor.run(agent, ctx, **kwargs)
                pipeline.results.append(result.output)
                previous_output = result.output

                if result.status != AgentStatus.COMPLETED:
                    pipeline.status = JobStatus.FAILED
                    pipeline.error = f"Step {i} ({step.agent_type}) failed: {result.error}"
                    return
            except Exception as exc:
                pipeline.status = JobStatus.FAILED
                pipeline.error = f"Step {i} ({step.agent_type}) exception: {exc}"
                return

        pipeline.status = JobStatus.COMPLETED
        pipeline.completed_at = datetime.now(timezone.utc)


job_queue = JobQueue()
