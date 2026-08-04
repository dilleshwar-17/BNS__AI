"""Legal research models: sessions, runs, reports (Phase 16)."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_INT_PK = BigInteger().with_variant(sa.Integer, "sqlite")

# Research run/session status values.
RESEARCH_PENDING = "PENDING"
RESEARCH_RUNNING = "RUNNING"
RESEARCH_COMPLETED = "COMPLETED"
RESEARCH_FAILED = "FAILED"
RESEARCH_STATUSES = (RESEARCH_PENDING, RESEARCH_RUNNING, RESEARCH_COMPLETED, RESEARCH_FAILED)


class ResearchSession(Base):
    """A user-scoped research thread. A session spawns one or more runs."""

    __tablename__ = "research_sessions"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResearchRun(Base):
    """A single research execution (planned subqueries -> evidence pool -> report)."""

    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RESEARCH_PENDING)
    subqueries: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_pool: Mapped[list | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResearchReport(Base):
    """Produced report tied to a research run."""

    __tablename__ = "research_reports"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    grounded: Mapped[bool] = mapped_column(nullable=False, default=False)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
