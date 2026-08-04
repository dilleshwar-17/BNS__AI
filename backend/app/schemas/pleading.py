"""Pleading API schemas (Phase 19)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PleadingTypeSchema(BaseModel):
    name: str
    title: str
    description: str


class PleadingTypesResponse(BaseModel):
    document_types: list[PleadingTypeSchema]


class PleadingGenerateRequest(BaseModel):
    case_id: int
    document_type: str


class PleadingRead(OrmModel):
    id: int
    case_id: int
    owner_id: uuid.UUID
    document_type: str
    title: str
    content: str
    grounded: bool
    citations: list[Any] = []
    created_at: datetime
    updated_at: datetime


class PleadingList(BaseModel):
    items: list[PleadingRead]
    total: int
