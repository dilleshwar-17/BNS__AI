"""Document analysis models (Phase 17)."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ANALYSIS_PENDING = "PENDING"
ANALYSIS_RUNNING = "RUNNING"
ANALYSIS_COMPLETED = "COMPLETED"
ANALYSIS_FAILED = "FAILED"


class DocumentAnalysis(Base):
    """A user-scoped analysis of an uploaded user document.

    Strict separation: the user's document text (``document_text``) is stored
    separately from any legal evidence used (``issues`` list carries only
    section references from the BNS corpus). No cross-contamination.
    """

    __tablename__ = "document_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ANALYSIS_PENDING)
    document_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    report: Mapped[str | None] = mapped_column(Text, nullable=True)
    grounded: Mapped[bool] = mapped_column(nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
