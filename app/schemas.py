from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class SourceItem(BaseModel):
    source: str
    page: int | None = None
    chunk: int | None = None
    distance: float | None = None
    preview: str


class AskResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceItem]


class AgentRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    conversation_id: str | None = None
