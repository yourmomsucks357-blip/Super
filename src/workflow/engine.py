"""
Workflow Engine — executes a WorkflowConfig graph node-by-node.

- Dependency resolution queue (Flowise AgentFlow V2 pattern)
- Saves a checkpoint BEFORE and AFTER each node (LangGraph pattern)
- Routes success/failure edges from outcome_judgment nodes
- Human approval gates pause execution and resume on external signal
- Fail-branch nodes isolate errors into error_message / error_type vars
"""
from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .dsl import WorkflowConfig, NodeDef, NodeType, ErrorStrategy
from .checkpoint import CheckpointStore, ExecutionCheckpoint, checkpoint_store
from src.agents.registry import AgentRegistry
from src.agents.base import AgentContext
from src.agents.executor import AgentExecutor
from src.memory.experiential import ExperientialRepository
from src.memory.working import WorkingContextMemory
from src.memory.retriever import retrieve
from src.cognitive.loop import CognitiveLoop, CognitiveDecision
from src.cognitive.plugins.evaluation import OutcomeEvaluator
from src.config import settings


@dataclass
class WorkflowRun:
    run_id:      str            = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str            = ""
    thread_id:   str            = field(default_factory=lambda: str(uuid.uuid4()))
    status:      str            = "pending"   # pending | running | completed | failed | paused
    flow_state:  Dict[str, Any] = field(default_factory=dict)
    outputs:     Dict[str, Any] = field(default_factory=dict)  # node_id → output
    error:       Optional[str]  = None
    paused_at:   Optional[str]  = None        # node_id where human gate paused
    created_at:  datetime       = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class WorkflowEngine:
    def __init__(
        self,
        store: Optional[CheckpointStore] = None,
        executor: Optional[AgentExecutor] = None,
        repository: Optional[ExperientialRepository] = None,
    ):
        self._store      = store      or checkpoint_store
        self._executor   = executor   or AgentExecutor()
        self._repository = repository or ExperientialRepository()
        self._runs: Dict[str, WorkflowRun] = {}
        self._resume_events: Dict[str, asyncio.Event] = {}
        self._resume_data: Dict[str, Any] = {}

    # ── Public API ────────────────────────────────────────────────────

    async def run(
        self,
        config: WorkflowConfig,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        run = WorkflowRun(workflow_id=config.workflow_id)
        run.flow_state = {**config.flow_state, **(inputs or {})}
        self._runs[run.run_id] = run
        run.status = "running"
        try:
            await self._execute_graph(config, run)
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
        finally:
            if run.status == "running":
                run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
        return run

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self._runs.get(run_id)

    def list_runs(self) -> List[WorkflowRun]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    async def resume(self, run_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Resume a paused workflow (human approval gate)."""
        event = self._resume_events.get(run_id)
        if event:
            self._resume_data[run_id] = data or {}
            event.set()

    # ── Graph execution ───────────────────────────────────────────────

    async def _execute_graph(self, config: WorkflowConfig, run: WorkflowRun) -> None:
        node_map  = {n.id: n for n in config.nodes}
        edge_map  = {n.id: [] for n in config.nodes}
        for edge in config.edges:
            edge_map[edge.source].append(edge)

        # Dependency resolution — topological-like BFS
        completed: Set[str] = set()
        pending = [n for n in config.nodes if not n.depends_on]
        step = 0

        while pending:
            # Find nodes whose dependencies are all met
            ready = [n for n in pending if all(d in completed for d in n.depends_on)]
            if not ready:
                # Check if we're paused — wait for resume
                if run.status == "paused":
                    break
                break  # deadlock guard

            for node in ready:
                pending.remove(node)
                step += 1

                # Checkpoint BEFORE node execution
                pre_cp = ExecutionCheckpoint(
                    workflow_id=config.workflow_id,
                    run_id=run.run_id,
                    thread_id=run.thread_id,
                    node_id=node.id,
                    step=step,
                    state=dict(run.flow_state),
                    status="pending",
                )
                self._store.save(pre_cp)

                # Execute node
                output, error = await self._execute_node(node, run, config)

                # Handle error strategies
                if error:
                    output, error = await self._handle_error(node, run, error, config)

                # Store output in run state
                run.outputs[node.id] = output
                run.flow_state[f"{{#{node.id}.output#}}"] = output
                if error:
                    run.flow_state[f"{{#{node.id}.error#}}"] = error

                # Commit checkpoint AFTER node execution
                pre_cp.status = "committed"
                pre_cp.pending = {}

                completed.add(node.id)

                # Resolve next nodes via edges (respecting conditions)
                outcome = run.flow_state.get(f"__outcome_{node.id}")
                for edge in edge_map.get(node.id, []):
                    target = node_map.get(edge.target)
                    if not target:
                        continue
                    if edge.condition in (None, "", "always"):
                        pending.append(target)
                    elif edge.condition == "success" and outcome == "success":
                        pending.append(target)
                    elif edge.condition == "failure" and outcome == "failure":
                        pending.append(target)

                if run.status in ("paused", "failed"):
                    return

    # ── Node dispatch ─────────────────────────────────────────────────

    async def _execute_node(
        self, node: NodeDef, run: WorkflowRun, config: WorkflowConfig
    ) -> tuple[Any, Optional[str]]:
        try:
            if node.type == NodeType.START:
                return run.flow_state, None

            elif node.type == NodeType.MEMORY_RETRIEVAL:
                objective = run.flow_state.get("message", run.flow_state.get("objective", ""))
                working   = WorkingContextMemory()
                results   = retrieve(objective, [], top_k=node.config.get("top_k", 5))
                exp_results = self._repository.retrieve(objective, top_k=node.config.get("top_k", 5))
                run.flow_state["__memory_context"] = [
                    {"title": r.item.title, "content": r.item.content, "score": r.relevance_score}
                    for r in exp_results
                ]
                return run.flow_state["__memory_context"], None

            elif node.type == NodeType.AGENT:
                agent_type = node.config.get("agent_type", "assistant")
                kwargs     = {**node.config.get("kwargs", {})}
                # Resolve DSL variable references: {{#node_id.field#}}
                kwargs.update({
                    k: run.flow_state.get(v, v) if isinstance(v, str) and v.startswith("{{#") else v
                    for k, v in kwargs.items()
                })
                kwargs["message"] = run.flow_state.get("message", "")
                try:
                    agent   = AgentRegistry.create(agent_type)
                    context = AgentContext(metadata={"workflow_run_id": run.run_id})
                    # Chat agents need a session
                    from src.agents.chat import ChatSession
                    session = ChatSession(session_id=run.thread_id)
                    session.add("user", kwargs["message"])
                    result  = await self._executor.run(agent, context, session=session, **kwargs)
                    output  = result.output
                    run.flow_state[f"__outcome_{node.id}"] = (
                        "success" if result.status.value == "completed" else "failure"
                    )
                    return output, None
                except Exception as exc:
                    run.flow_state[f"__outcome_{node.id}"] = "failure"
                    return None, str(exc)

            elif node.type == NodeType.OUTCOME_JUDGMENT:
                # Evaluate the most recent agent output
                agent_outputs = {k: v for k, v in run.outputs.items() if v is not None}
                last_output   = list(agent_outputs.values())[-1] if agent_outputs else None
                evaluator     = OutcomeEvaluator(self._repository)
                eval_result   = evaluator.judge(
                    objective=run.flow_state.get("message", ""),
                    output=last_output,
                    error=run.flow_state.get("__last_error"),
                )
                run.flow_state[f"__outcome_{node.id}"] = eval_result.outcome.value
                run.flow_state["__last_eval"] = {
                    "outcome": eval_result.outcome.value,
                    "score": eval_result.score,
                    "reflection": eval_result.reflection,
                }
                return run.flow_state["__last_eval"], None

            elif node.type == NodeType.SAFLA_CONSOLIDATION:
                branch    = node.config.get("branch", "both")
                last_eval = run.flow_state.get("__last_eval", {})
                outcome_str = last_eval.get("outcome", "success")
                from src.memory.models import MemoryOutcome
                outcome = MemoryOutcome(outcome_str)
                evaluator = OutcomeEvaluator(self._repository)
                eval_result = evaluator.consolidate(
                    eval_result=type("E", (), {
                        "outcome": outcome,
                        "score": last_eval.get("score", 1.0),
                        "reflection": last_eval.get("reflection", ""),
                        "new_strategy_id": None,
                        "new_guardrail_ids": [],
                    })(),
                    objective=run.flow_state.get("message", ""),
                    output_summary=str(list(run.outputs.values())[-1] if run.outputs else ""),
                )
                return {
                    "new_strategy_id": eval_result.new_strategy_id,
                    "new_guardrail_ids": eval_result.new_guardrail_ids,
                }, None

            elif node.type == NodeType.HUMAN_APPROVAL:
                run.status   = "paused"
                run.paused_at = node.id
                event = asyncio.Event()
                self._resume_events[run.run_id] = event
                prompt = node.config.get("prompt", "Human review required.")
                timeout = node.config.get("timeout", settings.agent_timeout)
                try:
                    await asyncio.wait_for(event.wait(), timeout=timeout)
                    resume_data = self._resume_data.pop(run.run_id, {})
                    approved    = resume_data.get("approved", True)
                    run.status  = "running"
                    run.flow_state[f"__outcome_{node.id}"] = "success" if approved else "failure"
                    return {"approved": approved, "feedback": resume_data.get("feedback", "")}, None
                except asyncio.TimeoutError:
                    run.flow_state[f"__outcome_{node.id}"] = "failure"
                    return None, f"Human approval gate timed out after {timeout}s."

            elif node.type == NodeType.CONDITION:
                expr   = node.config.get("expression", "true")
                result = bool(eval(expr, {"state": run.flow_state}))  # noqa: S307 – internal DSL only
                run.flow_state[f"__outcome_{node.id}"] = "success" if result else "failure"
                return {"result": result}, None

            elif node.type == NodeType.FAIL_BRANCH:
                error_msg  = run.flow_state.get("__last_error", "Unknown error")
                error_type = type(error_msg).__name__ if not isinstance(error_msg, str) else "ExecutionError"
                return {
                    "error_message": error_msg,
                    "error_type": error_type,
                }, None

            return None, f"Unknown node type: {node.type}"

        except Exception as exc:
            return None, str(exc)

    async def _handle_error(
        self, node: NodeDef, run: WorkflowRun, error: str, config: WorkflowConfig
    ) -> tuple[Any, Optional[str]]:
        run.flow_state["__last_error"] = error
        if not node.on_error:
            return None, error
        strategy = node.on_error.strategy
        if strategy == ErrorStrategy.DEFAULT_VALUE:
            return node.on_error.default_value, None
        elif strategy == ErrorStrategy.ABORT:
            run.status = "failed"
            run.error  = error
            return None, error
        elif strategy == ErrorStrategy.FAIL_BRANCH:
            # Route to fail_branch nodes is handled by edge conditions
            return None, None
        elif strategy == ErrorStrategy.RETRY:
            # Simple inline retry
            for attempt in range(1, node.on_error.retry_limit + 1):
                output, retry_err = await self._execute_node(node, run, config)
                if not retry_err:
                    return output, None
            return None, f"All {node.on_error.retry_limit} retries failed: {error}"
        return None, error


# Singleton engine
workflow_engine = WorkflowEngine()
