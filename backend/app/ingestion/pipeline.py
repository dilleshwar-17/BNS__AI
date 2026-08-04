"""Ingestion orchestrator: runs extract → clean → structure → chunk → persist.

Wires the deterministic Phase 4 pipeline into the ``IngestionJob`` lifecycle.
Chunks and job completion are committed together in a single transaction so a
failure never exposes partial corpus state (spec: fail closed). The source/
version is only advanced to PROCESSED here; approval/activation happens via
review (spec: only ACTIVE versions are authoritative).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.exceptions import DocumentProcessingFailedError, IngestionFailedError
from app.ingestion.chunker import chunk_document
from app.ingestion.cleaner import clean_text
from app.ingestion.extractor import extract_text
from app.ingestion.structure import detect_structure
from app.models.chunks import DocumentChunk
from app.models.sources import IngestionJob, SourceDocument, SourceVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class IngestResult:
    chunks_count: int
    sections_count: int
    elements_count: int
    characters_count: int
    extraction_seconds: float


async def run_ingestion(
    session: AsyncSession,
    job: IngestionJob,
    document: SourceDocument,
    *,
    source_version: SourceVersion,
) -> IngestResult:
    """Execute the full ingestion pipeline for one document/job atomically.

    A single commit at the end persists both the chunks and the ``completed``
    job state together. On any failure the transaction is rolled back and the
    job is marked ``failed`` (in a fresh commit) so callers can inspect why.
    """
    job.status = "processing"
    job.progress = 10
    job.started_at = datetime.now(timezone.utc)
    job.error_message = None
    await session.flush()

    t0 = time.monotonic()
    try:
        file_path = Path(document.stored_path)
        if not file_path.exists():
            raise DocumentProcessingFailedError("Source file is missing on disk.")
        raw_text = extract_text(file_path)
        cleaned = clean_text(raw_text)
        elements = detect_structure(cleaned)
        records = chunk_document(elements)

        parent_ids: dict[str, uuid.UUID] = {}
        created: list[DocumentChunk] = []
        for position, rec in enumerate(records):
            parent_id = parent_ids.get(_hash_key(rec.section_num, rec.chapter))
            chunk = DocumentChunk(
                source_version_id=source_version.id,
                document_id=document.id,
                parent_chunk_id=parent_id,
                chapter_id=rec.chapter,
                chapter_title=rec.chapter_title,
                section_id=rec.section_num,
                section_title=rec.section_title,
                subsection=rec.marker,
                element_type=rec.element_type,
                text=rec.text,
                content_hash=rec.content_hash,
                position=position,
            )
            session.add(chunk)
            created.append(chunk)
            if rec.is_parent:
                # Generate the UUID now so child rows can reference it.
                await session.flush()
                parent_ids[_hash_key(rec.section_num, rec.chapter)] = chunk.id

        sections = sum(1 for r in records if r.is_parent)
        stats = {
            "chunks": len(created),
            "sections": sections,
            "elements": len(elements),
            "characters": len(cleaned),
            "extraction_seconds": round(time.monotonic() - t0, 3),
        }
        job.chunks_count = len(created)
        job.stats = stats
        job.status = "completed"
        job.progress = 100
        job.finished_at = datetime.now(timezone.utc)
        await session.commit()

        return IngestResult(
            chunks_count=len(created),
            sections_count=sections,
            elements_count=len(elements),
            characters_count=len(cleaned),
            extraction_seconds=stats["extraction_seconds"],
        )
    except Exception as exc:  # noqa: BLE001
        # Roll back the failed transaction, then persist the failure reason.
        await session.rollback()
        job.status = "failed"
        job.progress = 0
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        await session.commit()
        raise IngestionFailedError(f"Ingestion failed: {exc}") from exc


def _hash_key(section_num: str | None, chapter: str | None) -> str:
    return f"{chapter or ''}:{section_num or ''}"


async def get_latest_version_for_document(session: AsyncSession, document: SourceDocument) -> SourceVersion:
    if document.source_id is None:
        raise IngestionFailedError("Document is not attached to a legal source.")
    result = await session.execute(
        select(SourceVersion)
        .where(SourceVersion.source_id == document.source_id)
        .order_by(SourceVersion.version_number.desc())
    )
    version = result.scalars().first()
    if version is None:
        raise IngestionFailedError("No source version exists for this document.")
    return version
