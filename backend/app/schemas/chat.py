from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

CHAT_MODES = Literal[
    "legal_guidance",
    "legal_drafting",
    "section_lookup",
    "case_law",
    "deep_research",
    "document_analysis",
    "legal_procedure",
    "rights_advisory",
    "comparison",
]


class ChatCreate(BaseModel):
    title: str = "New Chat"
    mode: CHAT_MODES = "legal_guidance"


class ChatResponse(BaseModel):
    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSend(BaseModel):
    message: str
    mode: CHAT_MODES = "legal_guidance"

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 10000:
            raise ValueError("Message must be at most 10,000 characters")
        return v.strip()


class ChatFeedback(BaseModel):
    message_id: str
    rating: Literal["helpful", "not_helpful", "partially_helpful"]
    comment: str | None = None

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 1000:
            raise ValueError("Comment must be at most 1,000 characters")
        return v
