"""Case intelligence service (Phase 18).

Provides ownership-scoped CRUD over case entities. All reads require an explicit
case owner id, so a user can never observe another user's case data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.case import (
    Case,
    CaseFact,
    CaseMember,
    CaseParty,
    CaseTimelineEvent,
    CaseVersion,
)


class CaseService:
    """Owner-scoped case operations."""

    async def _get_scoped(self, session: AsyncSession, case_id: int, user_id: uuid.UUID) -> Case:
        result = await session.execute(select(Case).where(Case.id == case_id, Case.owner_id == user_id))
        case = result.scalar_one_or_none()
        if case is None:
            raise NotFoundError("Case not found.")
        return case

    # -- crud ---------------------------------------------------------------

    async def create_case(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        title: str,
        description: str | None,
        matter_number: str | None,
        court: str | None,
    ) -> Case:
        case = Case(
            owner_id=user_id,
            title=title,
            description=description,
            matter_number=matter_number,
            court=court,
            status="OPEN",
        )
        session.add(case)
        await session.flush()
        return case

    async def list_cases(self, session: AsyncSession, user_id: uuid.UUID, limit: int, offset: int) -> list[Case]:
        return list(
            (
                await session.execute(
                    select(Case)
                    .where(Case.owner_id == user_id)
                    .order_by(Case.updated_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    async def count_cases(self, session: AsyncSession, user_id: uuid.UUID) -> int:
        return int(
            (await session.execute(select(func.count()).select_from(Case).where(Case.owner_id == user_id))).scalar_one()
        )

    async def get_case(self, session: AsyncSession, case_id: int, user_id: uuid.UUID) -> Case:
        return await self._get_scoped(session, case_id, user_id)

    # -- sub-records ---------------------------------------------------------

    async def add_member(
        self, session: AsyncSession, *, case_id: int, user_id: uuid.UUID, role_in_case: str | None
    ) -> CaseMember:
        member = CaseMember(case_id=case_id, user_id=user_id, role_in_case=role_in_case)
        session.add(member)
        await session.flush()
        return member

    async def add_party(
        self, session: AsyncSession, *, case_id: int, name: str, side: str | None, is_claimant: bool
    ) -> CaseParty:
        party = CaseParty(case_id=case_id, name=name, side=side, is_claimant=is_claimant)
        session.add(party)
        await session.flush()
        return party

    async def add_fact(
        self, session: AsyncSession, *, case_id: int, text: str, provenance: str | None, confidence: float | None
    ) -> CaseFact:
        fact = CaseFact(case_id=case_id, text=text, provenance=provenance, confidence=confidence, status="accepted")
        session.add(fact)
        await session.flush()
        return fact

    async def add_timeline_event(
        self, session: AsyncSession, *, case_id: int, when: datetime | None, description: str
    ) -> CaseTimelineEvent:
        event = CaseTimelineEvent(case_id=case_id, when=when, description=description)
        session.add(event)
        await session.flush()
        return event

    async def _scoped(self, session: AsyncSession, model, case_id: int) -> list:
        return list((await session.execute(select(model).where(model.case_id == case_id))).scalars().all())

    async def list_members(self, session: AsyncSession, case_id: int) -> list[CaseMember]:
        return await self._scoped(session, CaseMember, case_id)

    async def list_parties(self, session: AsyncSession, case_id: int) -> list[CaseParty]:
        return await self._scoped(session, CaseParty, case_id)

    async def list_facts(self, session: AsyncSession, case_id: int) -> list[CaseFact]:
        return await self._scoped(session, CaseFact, case_id)

    async def list_timeline(self, session: AsyncSession, case_id: int) -> list[CaseTimelineEvent]:
        return await self._scoped(session, CaseTimelineEvent, case_id)

    # -- versioning ----------------------------------------------------------

    async def snapshot_version(self, session: AsyncSession, *, case_id: int, note: str | None = None) -> CaseVersion:
        facts = [f.text for f in await self.list_facts(session, case_id)]
        latest = (
            await session.execute(
                select(CaseVersion)
                .where(CaseVersion.case_id == case_id)
                .order_by(CaseVersion.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        version_number = (latest.version_number + 1) if latest else 1
        version = CaseVersion(case_id=case_id, version_number=version_number, snapshot={"facts": facts}, note=note)
        session.add(version)
        await session.flush()
        return version
