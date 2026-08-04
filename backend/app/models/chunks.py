"""Ingestion chunk model: legal-aware chunks with provenance metadata (Phase 4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class DocumentChunk(Base):
    """A self-contained retrievable unit of a legal source.

    ``content_hash`` guards against duplicates; ``parent_chunk_id`` supports
    hierarchical parent/child chunking (e.g. full section as parent, with
    Explanation/Illustration split as children).
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_chunks.id"), index=True, nullable=True
    )

    # Structural metadata.
    chapter_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    chapter_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    section_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    section_title: Mapped[str | None] = mapped_column(String(400), nullable=True)
    subsection: Mapped[str | None] = mapped_column(String(30), nullable=True)
    element_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # SECTION / EXPLANATION / PROVISO / ILLUSTRATION / PARENT

    # Content.
    text: Mapped[str] = mapped_column(nullable=False)  # TEXT
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    page_numbers: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_document_chunks_src_section", "source_version_id", "section_id"),
        Index("ix_document_chunks_src_elem", "source_version_id", "element_type"),
    )
