import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from .chat import BaseChatAgent, ChatSession
from .base import AgentContext, AgentStatus
from .executor import executor
from .registry import AgentRegistry
from src.config import settings
from src.config.runtime import behavior
from src.cognitive.loop import CognitiveLoop, CognitiveDecision
from src.workflow.registry import WorkflowRegistry
from src.workflow.engine import workflow_engine


# ── Tool definitions passed to the LLM ───────────────────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Search YouTube for videos matching a query. Returns a list of video URLs and titles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":       {"type": "string",  "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max videos to return (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_agent",
            "description": "Call another registered agent and return its result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string", "description": "Registered agent type to call"},
                    "message": {"type": "string", "description": "Optional message for chat agents"},
                    "kwargs": {"type": "object", "description": "Keyword arguments passed to the agent"},
                },
                "required": ["agent_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": "List the currently registered agent types.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deploy_youtube_learner",
            "description": "Queue a youtube_learner agent to fetch and store the transcript of a video as knowledge under a subject.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url":     {"type": "string", "description": "Full YouTube video URL"},
                    "subject": {"type": "string", "description": "Subject/topic label for the stored knowledge"},
                },
                "required": ["url", "subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_workflows",
            "description": "List all saved workflows available in the system.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_workflow",
            "description": "Start execution of a specific workflow by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The unique ID of the workflow to run"},
                    "inputs": {"type": "object", "description": "Optional input variables for the workflow"},
                },
                "required": ["workflow_id"],
            },
        },
    },
]


def _search_youtube(query: str, max_results: int = 5) -> List[Dict]:
    try:
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        entries = results.get("entries", []) if results else []
        return [
            {"url": f"https://www.youtube.com/watch?v={e['id']}", "title": e.get("title", e["id"])}
            for e in entries if e and e.get("id")
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


def _deploy_youtube_learner(url: str, subject: str = "") -> Dict:
    from src.jobs.models import Job
    from src.jobs.queue import job_queue
    job = Job(agent_type="youtube_learner", kwargs={"url": url, "subject": subject})
    job_queue.enqueue(job)
    return {"job_id": job.job_id, "url": url, "subject": subject, "status": "queued"}


async def _call_agent(agent_type: str, message: str = "", kwargs: Optional[Dict[str, Any]] = None) -> Dict:
    kwargs = kwargs or {}
    try:
        agent = AgentRegistry.create(agent_type)
    except KeyError as exc:
        return {"error": str(exc)}

    context = AgentContext(agent_id=agent.agent_id, metadata={"invoked_by": "assistant"})
    try:
        if isinstance(agent, BaseChatAgent):
            session = ChatSession(session_id=str(uuid.uuid4()))
            chat_message = message or kwargs.pop("message", "") or kwargs.pop("prompt", "")
            result = await executor.run(agent, context, session=session, message=chat_message, **kwargs)
        else:
            result = await executor.run(agent, context, **kwargs)
    except Exception as exc:
        return {"agent_type": agent_type, "status": "failed", "error": str(exc)}

    payload = {
        "agent_type": agent_type,
        "status": result.status.value,
        "run_id": result.run_id,
        "output": result.output,
        "error": result.error,
    }
    if result.status == AgentStatus.COMPLETED:
        payload["status"] = "completed"
    return payload


def _list_agents() -> Dict:
    return {"agents": AgentRegistry.list_types()}


def _list_workflows() -> Dict:
    return {
        "workflows": [
            {"id": w.workflow_id, "name": w.name, "description": w.description}
            for w in WorkflowRegistry.list_all()
        ]
    }


async def _run_workflow(workflow_id: str, inputs: Optional[Dict] = None) -> Dict:
    config = WorkflowRegistry.get(workflow_id)
    if not config:
        return {"error": f"Workflow '{workflow_id}' not found"}
    
    run = await workflow_engine.run(config, inputs=inputs)
    return {
        "run_id": run.run_id,
        "status": run.status,
        "outputs": run.outputs,
        "error": run.error
    }


_TOOL_HANDLERS = {
    "search_youtube":        lambda args: _search_youtube(**args),
    "call_agent":            lambda args: _call_agent(**args),
    "list_agents":           lambda args: _list_agents(),
    "deploy_youtube_learner": lambda args: _deploy_youtube_learner(**args),
    "list_workflows":        lambda args: _list_workflows(),
    "run_workflow":          lambda args: _run_workflow(**args),
}


@AgentRegistry.register("assistant_legacy")
class AssistantAgent(BaseChatAgent):
    """
    General-purpose assistant with LLM-driven tool calling.
    The LLM decides when to search YouTube and deploy agents.
    """
    async def chat(self, session: ChatSession, message: str, **kwargs) -> str:
        # ── Cognitive loop guardrail check ────────────────────────────
        if behavior.refusal_threshold > 0:
            loop = CognitiveLoop()
            state = loop.evaluate(
                objective=message,
                available_agents=AgentRegistry.list_types(),
                execution_state={},
            )
            if state.decision == CognitiveDecision.ABORT:
                return f"[Refused] {state.decision_reason}"
            if state.decision == CognitiveDecision.PAUSE:
                return f"[Pending human review] {state.decision_reason}"

        # ── Build system prompt from weights ──────────────────────────
        system_prompt = behavior.build_system_prompt()
        print(f"DEBUG: Using System Prompt: {system_prompt}")

        # ── OpenRouter (direct HTTP calls) ────────────────────────
        if settings.openrouter_api_key:
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                }
                messages = [{"role": "system", "content": system_prompt}] + [
                    {"role": m.role, "content": m.content}
                    for m in session.history
                    if m.role in ("user", "assistant")
                ]

                # ── Agentic tool-call loop ─────────────────────────────
                while True:
                    payload = {
                        "model": settings.llm_model,
                        "messages": messages,
                        "tools": _TOOLS,
                        "tool_choice": "auto",
                        "temperature": behavior.temperature,
                        "max_tokens": behavior.max_tokens,
                    }
                    # Construct the correct OpenRouter endpoint URL, ensuring no double slashes
                    openrouter_url = settings.openrouter_base_url.rstrip('/') + "/chat/completions"
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            openrouter_url,
                            headers=headers,
                            json=payload,
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        msg = data["choices"][0]["message"]

                    if not msg.get("tool_calls"):
                        return msg.get("content", "")

                    # Execute each tool call and feed results back
                    messages.append(msg)
                    for tc in msg.get("tool_calls", []):
                        args = json.loads(tc["function"]["arguments"])
                        handler = _TOOL_HANDLERS.get(tc["function"]["name"])
                        result = handler(args) if handler else {"error": "unknown tool"}
                        if hasattr(result, "__await__"):
                            result = await result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result),
                        })

            except Exception as exc:
                return f"[LLM error] {exc}"

        # ── No key — stub ─────────────────────────────────────────────
        turn = len([m for m in session.history if m.role == "user"])
        return (
            f"[Turn {turn}] Received: \"{message}\". "
            f"Behavior: temp={behavior.temperature:.1f}, "
            f"safety={behavior.safety_weight:.1f}, "
            f"factuality={behavior.factuality_weight:.1f}. "
            "Set EAETS_OPENROUTER_API_KEY in .env to activate the LLM."
        )


@AgentRegistry.register("router")
class RouterAgent(BaseChatAgent):
    """
    Weighted keyword router. Each route has a list of (keyword, weight) tuples.
    The agent type with the highest cumulative match score wins.
    """

    WEIGHTED_ROUTES: Dict[str, List[Tuple[str, float]]] = {
        "compute": [
            ("calculate", 2.0), ("sum", 1.5), ("math", 1.5),
            ("number", 1.0), ("average", 1.5), ("total", 1.0),
        ],
        "echo": [
            ("repeat", 2.0), ("echo", 2.0), ("say", 1.5), ("copy", 1.0),
        ],
        "assistant": [
            ("help", 1.0), ("explain", 1.5), ("what", 0.5),
            ("how", 0.5), ("why", 0.5), ("tell", 1.0),
        ],
    }

    def _score(self, message: str) -> Dict[str, float]:
        lower = message.lower()
        scores: Dict[str, float] = {}
        for agent_type, keywords in self.WEIGHTED_ROUTES.items():
            score = sum(w for kw, w in keywords if kw in lower)
            if score > 0:
                scores[agent_type] = score
        return scores

    async def chat(self, session: ChatSession, message: str, **kwargs) -> str:
        scores = self._score(message)
        if not scores:
            return (
                f"[Router] No route matched for: \"{message}\". "
                f"Available: {list(self.WEIGHTED_ROUTES.keys())}"
            )
        best = max(scores, key=lambda k: scores[k])
        score_summary = ", ".join(f"{k}={v:.1f}" for k, v in sorted(
            scores.items(), key=lambda x: -x[1]))
        return (
            f"[Router → {best}] Scores: {score_summary}. "
            f"Dispatching \"{message}\" to `{best}`."
        )

