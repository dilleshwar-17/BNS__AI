"""Conversation memory models: short-term, summary, entity, case (Phase 13)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chat import Conversation

# Memory layers (spec: multi-layer recent / summary / entity / case).
MEMORY_RECENT = "RECENT"
MEMORY_SUMMARY = "SUMMARY"
MEMORY_ENTITY = "ENTITY"
MEMORY_CASE = "CASE"
MEMORY_LAYERS = (MEMORY_RECENT, MEMORY_SUMMARY, MEMORY_ENTITY, MEMORY_CASE)


class ConversationMemory(Base):
    """A single persisted memory fragment within a conversation.

    ``layer`` distinguishes short-term (RECENT), running SUMMARY, extracted
    ENTITY, and CASE facts. ENTITY rows may carry a ``confidence`` score.
    ``seq`` is an autoincrement integer primary key giving a stable trim/replay
    order (created_at has 1s precision on some backends, so it can't order tightly).
    """

    __tablename__ = "conversation_memories"

    seq: Mapped[int] = mapped_column(
        sa.BigInteger().with_variant(sa.Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    layer: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    entity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    section_refs: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    invalidated: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="memories")
