"""Source management service: upload, checksum, dedupe, state machine."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import (
    SOURCE_ACTIVE,
    SOURCE_APPROVED,
    SOURCE_ARCHIVED,
    SOURCE_FAILED,
    SOURCE_INACTIVE,
    SOURCE_PENDING_PROCESSING,
    SOURCE_PENDING_REVIEW,
    SOURCE_PROCESSED,
    SOURCE_PROCESSING,
    SOURCE_REJECTED,
    SOURCE_UPLOADED,
)
from app.core.exceptions import InvalidRequestError, NotFoundError, SourceNotActiveError
from app.models.sources import IngestionJob, LegalSource, SourceDocument, SourceVersion

# Allowed transitions for the source lifecycle state machine.
SOURCE_TRANSITIONS: dict[str, set[str]] = {
    SOURCE_UPLOADED: {SOURCE_PENDING_PROCESSING, SOURCE_FAILED, SOURCE_INACTIVE},
    SOURCE_PENDING_PROCESSING: {SOURCE_PROCESSING, SOURCE_FAILED, SOURCE_INACTIVE},
    SOURCE_PROCESSING: {SOURCE_PROCESSED, SOURCE_FAILED, SOURCE_INACTIVE},
    SOURCE_PROCESSED: {SOURCE_PENDING_REVIEW, SOURCE_REJECTED, SOURCE_INACTIVE, SOURCE_FAILED},
    SOURCE_PENDING_REVIEW: {SOURCE_APPROVED, SOURCE_REJECTED, SOURCE_INACTIVE},
    SOURCE_APPROVED: {SOURCE_ACTIVE, SOURCE_REJECTED, SOURCE_INACTIVE},
    SOURCE_ACTIVE: {SOURCE_INACTIVE, SOURCE_ARCHIVED, SOURCE_PENDING_REVIEW},
    SOURCE_FAILED: {SOURCE_UPLOADED, SOURCE_INACTIVE, SOURCE_ARCHIVED},
    SOURCE_REJECTED: {SOURCE_UPLOADED, SOURCE_INACTIVE, SOURCE_ARCHIVED},
    SOURCE_INACTIVE: {SOURCE_ACTIVE, SOURCE_ARCHIVED, SOURCE_UPLOADED},
    SOURCE_ARCHIVED: set(),
}


@dataclass
class UploadedDocument:
    document: SourceDocument
    is_duplicate: bool
    is_existing: bool


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_state_transition(current: str, target: str) -> None:
    if target == current:
        return
    if target not in SOURCE_TRANSITIONS.get(current, set()):
        raise InvalidRequestError(f"Illegal source status transition: {current} -> {target}")


async def create_uploaded_document(
    session: AsyncSession,
    *,
    filename: str,
    file_type: str,
    file_size: int,
    content: bytes,
    uploaded_by: uuid.UUID,
) -> UploadedDocument:
    """Persist an uploaded file, detect duplicates by checksum, and create a legal source."""
    checksum = sha256_hex(content)

    existing = (
        await session.execute(select(SourceDocument).where(SourceDocument.checksum == checksum))
    ).scalar_one_or_none()
    if existing is not None:
        return UploadedDocument(document=existing, is_duplicate=True, is_existing=True)

    settings = get_settings()
    storage_dir = settings.storage_dir
    stored_path = storage_dir / f"{checksum}.{file_type}"
    stored_path.parent.mkdir(parents=True, exist_ok=True)
    stored_path.write_bytes(content)

    legal_source = LegalSource(
        title=Path(filename).stem,
        short_title=Path(filename).stem,
        source_type="ACT",
        status=SOURCE_UPLOADED,
        created_by=uploaded_by,
    )
    session.add(legal_source)
    await session.flush()

    source_version = SourceVersion(
        source_id=legal_source.id,
        version_number=1,
        status=SOURCE_UPLOADED,
        checksum=checksum,
        file_path=str(stored_path),
        created_by=uploaded_by,
    )
    session.add(source_version)
    await session.flush()

    document = SourceDocument(
        source_id=legal_source.id,
        filename=filename,
        original_name=filename,
        file_type=file_type,
        file_size=file_size,
        checksum=checksum,
        stored_path=str(stored_path),
        status="uploaded",
        uploaded_by=uploaded_by,
    )
    session.add(document)
    await session.flush()
    return UploadedDocument(document=document, is_duplicate=False, is_existing=False)


async def get_document(session: AsyncSession, document_id: uuid.UUID) -> SourceDocument:
    result = await session.execute(select(SourceDocument).where(SourceDocument.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document not found.")
    return doc


async def delete_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    doc = await get_document(session, document_id)
    # Remove the orphaned file from disk if it exists.
    stored = Path(doc.stored_path)
    if stored.exists():
        stored.unlink(missing_ok=True)
    await session.delete(doc)


async def create_ingestion_job(
    session: AsyncSession, document_id: uuid.UUID, *, chunk_strategy: str, created_by: uuid.UUID
) -> IngestionJob:
    doc = await get_document(session, document_id)
    job = IngestionJob(
        document_id=doc.id,
        status="pending",
        progress=0,
        chunks_count=0,
        chunk_strategy=chunk_strategy,
    )
    session.add(job)
    await session.flush()
    return job


async def mark_processed(
    session: AsyncSession,
    *,
    source: LegalSource,
    source_version: SourceVersion,
) -> None:
    """Advance a source and its version to PROCESSED after successful ingestion.

    Walks the lifecycle state machine (UPLOADED → PENDING_PROCESSING →
    PROCESSING → PROCESSED) rather than jumping straight to PROCESSED.
    """
    for target in (SOURCE_PENDING_PROCESSING, SOURCE_PROCESSING, SOURCE_PROCESSED):
        if source.status != target and target not in SOURCE_TRANSITIONS.get(source.status, set()):
            continue
        if source.status == target:
            continue
        await update_source_status(session, source, target)
    if source.status != SOURCE_PROCESSED:
        await update_source_status(session, source, SOURCE_PROCESSED)
    if source_version.status not in {SOURCE_ACTIVE, SOURCE_PROCESSED, SOURCE_APPROVED}:
        source_version.status = SOURCE_PROCESSED
        session.add(source_version)
        await session.flush()


async def update_source_status(
    session: AsyncSession,
    source: LegalSource,
    target: str,
) -> LegalSource:
    """Transition a legal source to a new lifecycle status, enforcing the machine."""
    validate_transition = target != source.status
    if validate_transition and target not in SOURCE_TRANSITIONS.get(source.status, set()):
        raise InvalidRequestError(f"Illegal source status transition: {source.status} -> {target}")
    if target == SOURCE_ACTIVE:
        source.is_active = True
    elif source.is_active and target in {SOURCE_INACTIVE, SOURCE_ARCHIVED, SOURCE_REJECTED, SOURCE_FAILED}:
        source.is_active = False
    source.status = target
    source.updated_at = datetime.now(timezone.utc)
    session.add(source)
    await session.flush()
    return source


async def reserve_active_version(session: AsyncSession, source_id: uuid.UUID) -> SourceVersion:
    """Return the single authoritative ACTIVE version for a source, fail closed."""
    result = await session.execute(
        select(SourceVersion)
        .where(
            SourceVersion.source_id == source_id,
            SourceVersion.status == SOURCE_ACTIVE,
        )
        .order_by(SourceVersion.version_number.desc())
    )
    version = result.scalars().first()
    if version is None:
        raise SourceNotActiveError()
    return version
