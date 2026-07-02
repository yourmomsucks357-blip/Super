import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from src.agents import executor, registry
from src.agents.chat import ChatSession
from src.agents.base import AgentContext

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session store
_sessions: Dict[str, ChatSession] = {}


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

            try:
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
