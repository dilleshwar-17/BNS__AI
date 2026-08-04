"""Chat API schemas (Phase 8)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CitationRead(BaseModel):
    chunk_id: uuid.UUID | None = None
    section_id: str | None = None
    section_title: str | None = None
    element_type: str | None = None
    excerpt: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageRead(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    intent: str | None = None
    model: str | None = None
    grounded: bool | None = None
    created_at: datetime
    citations: list[CitationRead] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: uuid.UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = []


class ConversationList(BaseModel):
    conversations: list[ConversationRead]


class SendMessageRequest(BaseModel):
    content: str = ""


class StreamLine(BaseModel):
    type: str  # "delta" | "citations" | "done"
    content: str | None = None
    citations: list[CitationRead] = []
