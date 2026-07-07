from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.agents.hermes_agent import HermesCodingAgent
from src.agents.base import AgentContext

router = APIRouter(prefix="/coding", tags=["coding", "controller"])


class ChatRequest(BaseModel):
    prompt: str
    memoryFiles: Optional[List[str]] = None


class FileReadRequest(BaseModel):
    filePath: str


class FileWriteRequest(BaseModel):
    filePath: str
    content: str


class TerminalRequest(BaseModel):
    command: str
    args: List[str] = []


@router.post("/chat")
async def chat(request: ChatRequest):
    agent = HermesCodingAgent()
    result = await agent.execute(AgentContext(), prompt=request.prompt, memory_files=request.memoryFiles or [])
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/file/read")
async def file_read(request: FileReadRequest):
    agent = HermesCodingAgent()
    res = agent.execute(AgentContext(), tool="file_read", file_path=request.filePath)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/file/write")
async def file_write(request: FileWriteRequest):
    agent = HermesCodingAgent()
    res = agent.execute(AgentContext(), tool="file_write", file_path=request.filePath, content=request.content)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.post("/terminal")
async def terminal(request: TerminalRequest):
    agent = HermesCodingAgent()
    res = agent.execute(AgentContext(), tool="terminal", command=request.command, args=request.args)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res