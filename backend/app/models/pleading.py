"""Legal pleading models (Phase 19).

A ``CasePleading`` is a generated legal document assembled deterministically
from a case's facts, parties, timeline, and its retrieved candidate provisions.
Pleadings are retrieval-only: they are grounded on provisions already curated on
the case and never fabricate statutory text. If a case has no grounded
provisions or no facts, generation fails closed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_INT_PK = sa.BigInteger().with_variant(sa.Integer, "sqlite")


class CasePleading(Base):
    __tablename__ = "case_pleadings"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    grounded: Mapped[bool] = mapped_column(default=False, nullable=False)
    citations: Mapped[list[Any] | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
