"""Ingestion jobs router (frontend contract)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user, require_permission
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.ingestion.pipeline import get_latest_version_for_document, run_ingestion
from app.models.chunks import DocumentChunk
from app.models.sources import IngestionJob, LegalSource, SourceDocument
from app.models.user import User
from app.retrieval.hybrid import HybridRetriever
from app.schemas.sources import IngestionJobListResponse, IngestionJobRead
from app.source_management.service import (
    create_ingestion_job,
    get_document,
    mark_processed,
)

router = APIRouter()


async def _to_read(job: IngestionJob, filename: str | None = None) -> IngestionJobRead:
    return IngestionJobRead(
        id=job.id,
        document_id=job.document_id,
        filename=filename,
        status=job.status,
        progress=job.progress,
        chunks_count=job.chunks_count,
        error_message=job.error_message,
        stats=job.stats,
        chunk_strategy=job.chunk_strategy,
        created_at=job.created_at,
    )


async def _job_filename(session: AsyncSession, job: IngestionJob) -> str | None:
    result = await session.execute(select(SourceDocument.filename).where(SourceDocument.id == job.document_id))
    return result.scalar_one_or_none()


@router.post("/ingest/{document_id}", response_model=IngestionJobRead, summary="Start ingestion")
async def start_ingestion(
    document_id: uuid.UUID,
    chunk_strategy: str = "recursive",
    current_user: User = Depends(require_permission("ingestion.start")),
    session: AsyncSession = Depends(get_db),
) -> IngestionJobRead:
    doc = await get_document(session, document_id)
    job = await create_ingestion_job(session, document_id, chunk_strategy=chunk_strategy, created_by=current_user.id)
    await audit_service.record(
        session,
        action="ingestion.start",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="ingestion_job",
        resource_id=str(job.id),
    )
    await session.commit()

    # Execute the pipeline synchronously; the job ends completed or failed.
    source_version = await get_latest_version_for_document(session, doc)
    result = await run_ingestion(session, job, doc, source_version=source_version)
    if result.chunks_count > 0:
        source = (
            await session.execute(select(LegalSource).where(LegalSource.id == doc.source_id))
        ).scalar_one_or_none()
        if source is not None:
            await mark_processed(session, source=source, source_version=source_version)
            await session.commit()

        # Embed chunks into vector + lexical stores (best-effort, non-blocking).
        try:
            chunks = (
                (await session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id)))
                .scalars()
                .all()
            )
            if chunks:
                retriever = HybridRetriever()
                retriever.upsert_chunks(
                    chunk_ids=[c.id for c in chunks],
                    texts=[c.text for c in chunks],
                    metadatas=[
                        {
                            "source_version_id": str(c.source_version_id),
                            "document_id": str(c.document_id),
                            "chapter_id": c.chapter_id,
                            "chapter_title": c.chapter_title,
                            "section_id": c.section_id,
                            "section_title": c.section_title,
                            "subsection": c.subsection,
                            "element_type": c.element_type,
                            "position": c.position,
                            "content_hash": c.content_hash,
                        }
                        for c in chunks
                    ],
                )
        except Exception:  # noqa: BLE001
            # Log but don't fail the ingestion; embeddings can be rebuilt later.
            import logging

            logging.getLogger(__name__).exception("Embedding failed for doc %s", doc.id)

    return await _to_read(job, filename=doc.filename)


async def _list_response(session: AsyncSession, result_jobs: list[IngestionJob]) -> IngestionJobListResponse:
    out: list[IngestionJobRead] = []
    for j in result_jobs:
        out.append(await _to_read(j, filename=await _job_filename(session, j)))
    return IngestionJobListResponse(jobs=out)


@router.get("/jobs", response_model=IngestionJobListResponse, summary="List my ingestion jobs")
async def list_jobs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionJobListResponse:
    result = await session.execute(select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(limit))
    return await _list_response(session, list(result.scalars().all()))


@router.get("/admin/jobs", response_model=IngestionJobListResponse, summary="Admin list ingestion jobs")
async def admin_list_jobs(
    limit: int = 20,
    current_user: User = Depends(require_permission("ingestion.read")),
    session: AsyncSession = Depends(get_db),
) -> IngestionJobListResponse:
    result = await session.execute(select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(limit))
    return await _list_response(session, list(result.scalars().all()))


@router.get("/jobs/{job_id}", response_model=IngestionJobRead, summary="Get an ingestion job")
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionJobRead:
    result = await session.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Ingestion job not found.")
    return await _to_read(job, await _job_filename(session, job))
