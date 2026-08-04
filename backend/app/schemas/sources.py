"""Source management schemas (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Uploaded document (frontend 'documents' contract)."""

    id: uuid.UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: list[DocumentRead]
    total: int


class UploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    is_duplicate: bool


class IngestionJobRead(BaseModel):
    id: uuid.UUID
    filename: str | None = None
    document_id: uuid.UUID
    status: str
    progress: int
    chunks_count: int
    error_message: str | None = None
    stats: dict | None = None
    chunk_strategy: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionJobListResponse(BaseModel):
    jobs: list[IngestionJobRead]


class LegalSourceRead(BaseModel):
    id: uuid.UUID
    title: str
    short_title: str | None = None
    source_type: str
    status: str
    authority_level: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
