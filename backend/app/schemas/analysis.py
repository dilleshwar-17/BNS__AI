"""Document analysis schemas (Phase 17)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentAnalysisCreateRequest(BaseModel):
    document_id: uuid.UUID


class DocumentAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    issues: list[dict] | None = None
    report: str | None = None
    grounded: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime
