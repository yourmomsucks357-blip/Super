import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .base import AgentContext, AgentResult, AgentStatus, BaseAgent
from src.config import settings
from src.telemetry import collector


class AgentExecutor:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_agents)
        self._active_runs: Dict[str, asyncio.Task] = {}

    async def run(
        self,
        agent: BaseAgent,
        context: Optional[AgentContext] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> AgentResult:
        if context is None:
            context = AgentContext(agent_id=agent.agent_id)

        timeout = timeout or settings.agent_timeout
        started_at = datetime.now(timezone.utc)
        t0 = time.monotonic()

        result = AgentResult(
            run_id=context.run_id,
            agent_id=agent.agent_id,
            status=AgentStatus.PENDING,
            started_at=started_at,
        )

        async with self._semaphore:
            result.status = AgentStatus.RUNNING
            collector.agent_start(agent.agent_id, context.run_id, agent.agent_type)
            try:
                await agent.on_start(context)
                output = await asyncio.wait_for(
                    agent.execute(context, **kwargs),
                    timeout=timeout,
                )
                result.output = output
                result.status = AgentStatus.COMPLETED
            except asyncio.TimeoutError:
                result.status = AgentStatus.TIMEOUT
                result.error = f"Agent timed out after {timeout}s"
                collector.agent_failed(agent.agent_id, context.run_id, result.error)
                await agent.on_error(context, TimeoutError(result.error))
            except asyncio.CancelledError:
                result.status = AgentStatus.CANCELLED
                result.error = "Agent execution was cancelled"
                raise
            except Exception as exc:
                result.status = AgentStatus.FAILED
                result.error = str(exc)
                collector.agent_failed(agent.agent_id, context.run_id, result.error)
                await agent.on_error(context, exc)
            finally:
                result.completed_at = datetime.now(timezone.utc)
                result.duration_ms = (time.monotonic() - t0) * 1000
                if result.status == AgentStatus.COMPLETED:
                    collector.agent_complete(agent.agent_id, context.run_id, result.duration_ms)
                    await agent.on_complete(context, result)

        return result

    async def run_with_retry(
        self,
        agent: BaseAgent,
        context: Optional[AgentContext] = None,
        retries: Optional[int] = None,
        **kwargs,
    ) -> AgentResult:
        max_retries = retries if retries is not None else settings.retry_limit
        last_result: Optional[AgentResult] = None

        for attempt in range(max_retries + 1):
            ctx = context or AgentContext(agent_id=agent.agent_id)
            if attempt > 0:
                ctx.metadata["retry_attempt"] = attempt
            last_result = await self.run(agent, ctx, **kwargs)
            if last_result.status == AgentStatus.COMPLETED:
                return last_result
            if last_result.status == AgentStatus.CANCELLED:
                break

        return last_result

    async def cancel(self, run_id: str) -> bool:
        task = self._active_runs.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False


executor = AgentExecutor()
