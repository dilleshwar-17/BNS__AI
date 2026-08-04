"""Case report models (Phase 20).

A ``CaseReport`` is a persisted, human-readable client-facing document generated
by aggregating a case's facts, parties, timeline, contradictions, missing facts,
provisions, scenarios and follow-ups. Reports are deterministic and
retrieval-only; they surface only data already on the case.
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


class CaseReport(Base):
    __tablename__ = "case_reports"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list[Any] | None] = mapped_column(sa.JSON, nullable=True)
    citations: Mapped[list[Any] | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
