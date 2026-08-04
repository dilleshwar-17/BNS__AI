"""Report API schemas (Phase 20)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReportTypeSchema(BaseModel):
    name: str
    title: str
    description: str


class ReportTypesResponse(BaseModel):
    report_types: list[ReportTypeSchema]


class ReportGenerateRequest(BaseModel):
    case_id: int
    report_type: str


class ReportRead(OrmModel):
    id: int
    case_id: int
    owner_id: uuid.UUID
    report_type: str
    title: str
    content: str
    sections: list[Any] = []
    citations: list[Any] = []
    created_at: datetime
    updated_at: datetime


class ReportList(BaseModel):
    items: list[ReportRead]
    total: int
