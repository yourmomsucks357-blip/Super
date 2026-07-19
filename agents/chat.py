from abc import abstractmethod
from typing import Any, AsyncIterator, List
from dataclasses import dataclass, field

from .base import AgentContext, BaseAgent


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatSession:
    session_id: str
    history: List[ChatMessage] = field(default_factory=list)

    def add(self, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(role=role, content=content)
        self.history.append(msg)
        return msg


class BaseChatAgent(BaseAgent):
    """Agent that participates in a multi-turn conversation."""

    @abstractmethod
    async def chat(self, session: ChatSession, message: str, **kwargs) -> str:
        """Process a user message and return the assistant reply."""

    async def execute(self, context: AgentContext, **kwargs) -> Any:
        session: ChatSession = kwargs.pop("session")
        message: str = kwargs.pop("message")
        reply = await self.chat(session, message, **kwargs)
        session.add("assistant", reply)
        return {"reply": reply, "history": [
            {"role": m.role, "content": m.content} for m in session.history
        ]}
