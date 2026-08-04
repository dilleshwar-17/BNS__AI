"""Case intelligence schemas (Phase 18)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CaseCreate(BaseModel):
    title: str
    description: str | None = None
    matter_number: str | None = None
    court: str | None = None


class CaseRead(OrmModel):
    id: int
    owner_id: uuid.UUID
    title: str
    description: str | None = None
    matter_number: str | None = None
    court: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class CaseList(BaseModel):
    cases: list[CaseRead]
    total: int


class CaseMemberCreate(BaseModel):
    user_id: uuid.UUID
    role_in_case: str | None = None


class MemberRead(OrmModel):
    id: int
    case_id: int
    user_id: uuid.UUID
    role_in_case: str | None = None


class PartyCreate(BaseModel):
    name: str
    side: str | None = None
    is_claimant: bool = False


class PartyRead(OrmModel):
    id: int
    case_id: int
    name: str
    side: str | None = None
    is_claimant: bool


class FactCreate(BaseModel):
    text: str
    provenance: str | None = None
    confidence: float | None = None


class FactRead(OrmModel):
    id: int
    case_id: int
    text: str
    provenance: str | None = None
    confidence: float | None = None
    status: str
    created_at: datetime


class FactList(BaseModel):
    facts: list[FactRead]


class TimelineCreate(BaseModel):
    when: datetime | None = None
    description: str


class TimelineRead(OrmModel):
    id: int
    case_id: int
    when: datetime | None = None
    description: str


class TimelineList(BaseModel):
    events: list[TimelineRead]


class EvidenceRead(OrmModel):
    id: int
    case_id: int
    document_id: uuid.UUID | None = None
    description: str | None = None


class EvidenceList(BaseModel):
    items: list[EvidenceRead]


class ContradictionRead(OrmModel):
    id: int
    case_id: int
    fact_a_id: int | None = None
    fact_b_id: int | None = None
    summary: str | None = None


class ContradictionList(BaseModel):
    items: list[ContradictionRead]


class ProvisionRead(OrmModel):
    id: int
    case_id: int
    section_id: str | None = None
    source_chunk_id: uuid.UUID | None = None
    snippet: str | None = None


class AnalysisSummary(BaseModel):
    provisions: list[ProvisionRead]


class CaseDetail(CaseRead):
    members: list[MemberRead] = []
    parties: list[PartyRead] = []
    facts: list[FactRead] = []
