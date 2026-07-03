import uuid
import json
from typing import Dict, List, Optional, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from src.agents import executor, registry
from src.agents.chat import ChatSession
from src.agents.base import AgentContext

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store
_sessions: Dict[str, ChatSession] = {}


def _parse_agent_command(message: str) -> Tuple[Optional[str], Dict[str, object]]:
    text = message.strip()
    if not (text.startswith("/agent ") or text.startswith("/call ")):
        return None, {}

    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        return None, {}

    agent_type = parts[1].strip()
    if len(parts) == 2:
        return agent_type, {"message": ""}

    payload = parts[2].strip()
    if payload.startswith("{"):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return agent_type, parsed
        except json.JSONDecodeError:
            pass
    return agent_type, {"message": payload}


async def _run_agent(agent_type: str, message: str, kwargs: Dict[str, object], session: ChatSession):
    agent = registry.create(agent_type)
    ctx = AgentContext(agent_id=agent.agent_id)
    if agent_type in ("assistant", "router") and "message" not in kwargs:
        kwargs = {**kwargs, "message": message}
    result = await executor.run(agent, ctx, session=session, **kwargs)
    if result.output:
        if isinstance(result.output, dict):
            reply = result.output.get("reply")
            if reply is None:
                reply = json.dumps(result.output, indent=2, default=str)
        else:
            reply = str(result.output)
    else:
        reply = result.error or "Agent failed"
    return reply


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    agent_type: str = "assistant"
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: list


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    session = _sessions.setdefault(session_id, ChatSession(session_id=session_id))
    session.add("user", req.message)

    direct_agent_type, direct_kwargs = _parse_agent_command(req.message)
    if direct_agent_type:
        try:
            reply = await _run_agent(direct_agent_type, req.message, direct_kwargs, session)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Agent type '{direct_agent_type}' not found")

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            history=[{"role": m.role, "content": m.content} for m in session.history],
        )

    try:
        agent = registry.create(req.agent_type)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent type '{req.agent_type}' not found")

    ctx = AgentContext(agent_id=agent.agent_id)
    result = await executor.run(agent, ctx, session=session, message=req.message)

    if result.output:
        return ChatResponse(
            session_id=session_id,
            reply=result.output.get("reply", ""),
            history=result.output.get("history", []),
        )
    raise HTTPException(status_code=500, detail=result.error or "Agent failed")


@router.get("/sessions")
async def list_sessions():
    return [
        {"session_id": sid, "turns": len(s.history)}
        for sid, s in _sessions.items()
    ]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id,
            "history": [{"role": m.role, "content": m.content} for m in session.history]}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"deleted": session_id}


# ── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str, agent_type: str = "assistant"):
    await websocket.accept()
    session = _sessions.setdefault(session_id, ChatSession(session_id=session_id))

    try:
        while True:
            message = await websocket.receive_text()
            session.add("user", message)

            direct_agent_type, direct_kwargs = _parse_agent_command(message)

            try:
                if direct_agent_type:
                    reply = await _run_agent(direct_agent_type, message, direct_kwargs, session)
                else:
                    agent = registry.create(agent_type)
                    ctx = AgentContext(agent_id=agent.agent_id)
                    result = await executor.run(agent, ctx, session=session, message=message)
                    reply = result.output.get("reply", "") if result.output else (result.error or "error")
            except Exception as exc:
                reply = f"[Error] {exc}"

            await websocket.send_json({
                "session_id": session_id,
                "reply": reply,
                "turns": len(session.history),
            })
    except WebSocketDisconnect:
        pass
