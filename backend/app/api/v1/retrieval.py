"""Retrieval API router (Phase 6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.user import User
from app.retrieval.service import RetrievalOutcome, RetrievalService
from app.schemas.retrieval import (
    RetrievalQueryRequest,
    RetrievalResponse,
    RetrievalSectionResponse,
    RetrievedChunk,
)

router = APIRouter()


def _to_chunks(outcome: RetrievalOutcome) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=r.chunk_id,
            text=r.text,
            score=round(r.score, 4),
            section_id=r.metadata.get("section_id"),
            section_title=r.metadata.get("section_title"),
            chapter_id=r.metadata.get("chapter_id"),
            chapter_title=r.metadata.get("chapter_title"),
            element_type=r.metadata.get("element_type"),
            source_version_id=_uuid_or_none(r.metadata.get("source_version_id")),
            document_id=_uuid_or_none(r.metadata.get("document_id")),
        )
        for r in outcome.results
    ]


def _uuid_or_none(v: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(v)) if v else None
    except (ValueError, TypeError):
        return None


@router.post("/search", response_model=RetrievalResponse, summary="Hybrid retrieval search")
async def search(
    payload: RetrievalQueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RetrievalResponse:
    service = RetrievalService()
    outcome = service.retrieve(
        payload.query,
        top_k=payload.top_k,
        fail_closed=payload.fail_closed,
    )
    await audit_service.record(
        session,
        action="retrieval.search",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="retrieval",
        resource_id="search",
        metadata={"query": payload.query, "hits": len(outcome.results)},
    )
    await session.commit()
    return RetrievalResponse(
        query=outcome.query,
        gated=outcome.gated,
        note=outcome.note,
        results=_to_chunks(outcome),
    )


@router.post("/section", response_model=RetrievalSectionResponse, summary="Exact section lookup")
async def section_lookup(
    payload: RetrievalQueryRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RetrievalSectionResponse:
    if not payload.section:
        from app.core.exceptions import InvalidRequestError

        raise InvalidRequestError("section is required.")
    service = RetrievalService()
    results = service.retrieve_section(payload.section)
    await audit_service.record(
        session,
        action="retrieval.section",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="retrieval",
        resource_id=payload.section,
    )
    await session.commit()
    return RetrievalSectionResponse(
        section_id=payload.section,
        results=[
            RetrievedChunk(
                chunk_id=r.chunk_id,
                text=r.text,
                score=round(r.score, 4),
                section_id=r.metadata.get("section_id"),
                section_title=r.metadata.get("section_title"),
                chapter_id=r.metadata.get("chapter_id"),
                chapter_title=r.metadata.get("chapter_title"),
                element_type=r.metadata.get("element_type"),
            )
            for r in results
        ],
    )


@router.get("/health", summary="Retrieval subsystem health")
async def retrieval_health() -> dict[str, str]:
    from app.core.config import get_settings

    s = get_settings()
    return {
        "status": "ok",
        "semantic_enabled": str(s.rag_semantic_enabled),
        "lexical_enabled": str(s.rag_lexical_enabled),
        "top_k": str(s.rag_top_k),
        "min_score": str(s.rag_min_score),
    }
