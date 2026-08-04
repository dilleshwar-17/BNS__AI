"""Case intelligence models (Phase 18).

Domains:
    Case                 - a user-owned legal matter with team members.
    CaseParty             - parties involved (prosecution/defence/third party).
    CaseFact             - a fact with provenance (source + confidence).
    CaseEvidence         - evidence tied to a source document.
    CaseTimelineEvent    - dated event in the case timeline.
    CaseContradiction     - conflict between two extracted/entered facts.
    CaseMissingFact       - a gap flagged for investigation.
    CandidateProvision    - a BNS/legal section candidate for the case.
    ElementOfOffence      - element-of-offence mapping (e.g. theft: taking+intent).
    AlternativeScenario   - hypothesised alternative reading of events.
    OutcomeScenario       - predicted/possible outcome given provisions.
    CaseFollowUp          - an actionable follow-up task.
    CaseVersion           - a persistable version snapshot of the case.

All numeric ids use a portable autoincrement BigInteger (SQLite variant) to match
other ORM objects; user-scoped tables FK to ``users.id`` (UUID).
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_INT_PK = sa.BigInteger().with_variant(sa.Integer, "sqlite")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    matter_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    court: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CaseMember(Base):
    __tablename__ = "case_members"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role_in_case: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseParty(Base):
    __tablename__ = "case_parties"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    side: Mapped[str | None] = mapped_column(String(30), nullable=True)  # prosecution/defence/third
    is_claimant: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseFact(Base):
    __tablename__ = "case_facts"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[str | None] = mapped_column(String(300), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="accepted", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseEvidence(Base):
    __tablename__ = "case_evidence"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseTimelineEvent(Base):
    __tablename__ = "case_timeline_events"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    when: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseContradiction(Base):
    __tablename__ = "case_contradictions"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    fact_a_id: Mapped[int | None] = mapped_column(ForeignKey("case_facts.id"), nullable=True)
    fact_b_id: Mapped[int | None] = mapped_column(ForeignKey("case_facts.id"), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseMissingFact(Base):
    __tablename__ = "case_missing_facts"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    what: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateProvision(Base):
    __tablename__ = "candidate_provisions"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    section_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ElementOfOffence(Base):
    __tablename__ = "element_of_offence"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    section_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    element: Mapped[str] = mapped_column(String(200), nullable=False)
    satisfied: Mapped[bool] = mapped_column(default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlternativeScenario(Base):
    __tablename__ = "alternative_scenarios"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutcomeScenario(Base):
    __tablename__ = "outcome_scenarios"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    likelihood: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseFollowUp(Base):
    __tablename__ = "case_follow_ups"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    done: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseVersion(Base):
    __tablename__ = "case_versions"

    id: Mapped[int] = mapped_column(_INT_PK, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    snapshot: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
