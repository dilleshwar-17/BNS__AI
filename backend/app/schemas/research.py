"""Legal research API schemas (Phase 16)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResearchSessionCreate(BaseModel):
    title: str | None = None
    topic: str


class ResearchSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None = None
    topic: str
    created_at: datetime
    updated_at: datetime


class ResearchSessionList(BaseModel):
    sessions: list[ResearchSessionRead]


class ResearchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    status: str
    subqueries: list[str] | None = None
    evidence_pool: list[dict] | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class ResearchRunList(BaseModel):
    runs: list[ResearchRunRead]


class ResearchReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    content: str
    grounded: bool
    citations: list[dict] | None = None
    created_at: datetime


class ResearchTriggerRequest(BaseModel):
    session_id: int
    topic: str | None = None
