"""Retrieval API schemas (Phase 6)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class RetrievalQueryRequest(BaseModel):
    query: str = ""
    top_k: int | None = None
    section: str | None = None
    fail_closed: bool = True


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    text: str
    score: float
    section_id: str | None = None
    section_title: str | None = None
    chapter_id: str | None = None
    chapter_title: str | None = None
    element_type: str | None = None
    source_version_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class RetrievalResponse(BaseModel):
    query: str
    gated: bool
    note: str | None = None
    results: list[RetrievedChunk]


class RetrievalSectionResponse(BaseModel):
    section_id: str
    results: list[RetrievedChunk]
