"""Source management models: legal sources, documents, versions, jobs (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PortableJSON = JSON().with_variant(JSONB, "postgresql")

if TYPE_CHECKING:
    pass


class LegalSource(Base):
    """An authoritative legal instrument (e.g. the Bharatiya Nyaya Sanhita)."""

    __tablename__ = "legal_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    short_title: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="ACT", nullable=False)
    # Lifecycle: UPLOADED → PENDING_PROCESSING → PROCESSING → PROCESSED →
    # PENDING_REVIEW → APPROVED → ACTIVE | FAILED | REJECTED | INACTIVE | ARCHIVED.
    status: Mapped[str] = mapped_column(String(40), default="UPLOADED", nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    authority_level: Mapped[str] = mapped_column(String(40), default="PRIMARY_OFFICIAL", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["SourceVersion"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class SourceVersion(Base):
    """A concrete version of a legal source; only ACTIVE versions are authoritative."""

    __tablename__ = "source_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("legal_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    # UPLOADED → PROCESSING → PROCESSED → APPROVED → ACTIVE | FAILED | REJECTED | INACTIVE | ARCHIVED.
    status: Mapped[str] = mapped_column(String(40), default="UPLOADED", nullable=False, index=True)
    checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extraction_meta: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[LegalSource] = relationship(back_populates="versions")


class SourceDocument(Base):
    """An uploaded file that is a candidate source (frontend 'documents' contract)."""

    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("legal_sources.id"), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    original_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="uploaded", nullable=False, index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_source_documents_source_status", "source_id", "status"),)


class IngestionJob(Base):
    """A pipeline run that processes a document into retrievable chunks."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # pending → processing → completed | failed | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(default=0, nullable=False)
    chunks_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    chunk_strategy: Mapped[str] = mapped_column(String(30), default="recursive", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[SourceDocument] = relationship(back_populates="ingestion_jobs")
