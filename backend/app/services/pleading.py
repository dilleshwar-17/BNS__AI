"""Legal pleading generation service (Phase 19).

Assembles a legal document deterministically from a case's curated facts,
parties, timeline and candidate provisions. It performs *no* free-form LLM
synthesis of legal content: every referenced section comes from the case's
retrieved ``CandidateProvision`` set, so pleadings stay retrieval-only and
fail closed. If a case has no grounded provisions or no accepted facts, the
service raises ``InsufficientBNSEvidenceError`` rather than emitting an
ungrounded document.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InsufficientBNSEvidenceError,
    NotFoundError,
)
from app.models.case import (
    CandidateProvision,
    Case,
    CaseFact,
    CaseParty,
    CaseTimelineEvent,
)
from app.models.pleading import CasePleading

DOCUMENT_TYPES: dict[str, dict[str, str]] = {
    "AFFIDAVIT": {
        "title": "Affidavit in Support",
        "description": "Sworn statement of the stated facts with statutory grounding.",
    },
    "COMPLAINT": {
        "title": "Complaint",
        "description": "Formal complaint setting out the facts and provisions engaged.",
    },
    "BAIL_APPLICATION": {
        "title": "Bail Application",
        "description": "Application for bail referencing the accused, facts and provisions.",
    },
    "CASE_SUMMARY": {
        "title": "Case Summary Brief",
        "description": "Chronological brief of facts, parties and provisions.",
    },
}


class PleadingsService:
    """Owner-scoped generation of case pleadings."""

    async def _get_scoped_case(self, session: AsyncSession, case_id: int, owner_id: uuid.UUID) -> Case:
        result = await session.execute(select(Case).where(Case.id == case_id, Case.owner_id == owner_id))
        case = result.scalar_one_or_none()
        if case is None:
            raise NotFoundError("Case not found.")
        return case

    async def _facts(self, session: AsyncSession, case_id: int) -> list[CaseFact]:
        return list(
            (await session.execute(select(CaseFact).where(CaseFact.case_id == case_id).order_by(CaseFact.id)))
            .scalars()
            .all()
        )

    async def _parties(self, session: AsyncSession, case_id: int) -> list[CaseParty]:
        return list(
            (await session.execute(select(CaseParty).where(CaseParty.case_id == case_id).order_by(CaseParty.id)))
            .scalars()
            .all()
        )

    async def _timeline(self, session: AsyncSession, case_id: int) -> list[CaseTimelineEvent]:
        events = list(
            (await session.execute(select(CaseTimelineEvent).where(CaseTimelineEvent.case_id == case_id)))
            .scalars()
            .all()
        )
        return sorted(events, key=lambda e: (e.when is not None, e.when or datetime.min, e.id))

    async def _provisions(self, session: AsyncSession, case_id: int) -> list[CandidateProvision]:
        return list(
            (
                await session.execute(
                    select(CandidateProvision)
                    .where(CandidateProvision.case_id == case_id)
                    .order_by(CandidateProvision.id)
                )
            )
            .scalars()
            .all()
        )

    async def generate(
        self,
        session: AsyncSession,
        *,
        case_id: int,
        owner_id: uuid.UUID,
        document_type: str,
    ) -> CasePleading:
        key = document_type.upper()
        if key not in DOCUMENT_TYPES:
            raise NotFoundError(f"Unsupported document type: {document_type}")

        case = await self._get_scoped_case(session, case_id, owner_id)
        facts = await self._facts(session, case.id)
        parties = await self._parties(session, case.id)
        timeline = await self._timeline(session, case.id)
        provisions = await self._provisions(session, case.id)

        grounded_provisions = [p for p in provisions if p.section_id]
        if not facts:
            raise InsufficientBNSEvidenceError("No accepted facts on the case. Add facts before generating a pleading.")
        if not grounded_provisions:
            raise InsufficientBNSEvidenceError(
                "No grounded provisions on the case. Add candidate provisions before " "generating a pleading."
            )

        citations = [p.section_id for p in grounded_provisions if p.section_id]
        title = DOCUMENT_TYPES[key]["title"]
        content = self._assemble(key, case, facts, parties, timeline, grounded_provisions, citations)

        pleading = CasePleading(
            case_id=case.id,
            owner_id=owner_id,
            document_type=key,
            title=title,
            content=content,
            grounded=True,
            citations=citations,
        )
        session.add(pleading)
        await session.flush()
        return pleading

    def _assemble(
        self,
        key: str,
        case: Case,
        facts: list[CaseFact],
        parties: list[CaseParty],
        timeline: list[CaseTimelineEvent],
        provisions: list[CandidateProvision],
        citations: list[str],
    ) -> str:
        lines: list[str] = []
        lines.append(DOCUMENT_TYPES[key]["title"].upper())
        lines.append("=" * len(DOCUMENT_TYPES[key]["title"]))
        lines.append("")
        lines.append(f"Case: {case.title}")
        if case.matter_number:
            lines.append(f"Matter Number: {case.matter_number}")
        if case.court:
            lines.append(f"Court: {case.court}")
        lines.append("")

        if parties:
            lines.append("Parties:")
            for p in parties:
                role = "Claimant/Complainant" if p.is_claimant else (p.side or "Party")
                lines.append(f"  - {p.name} ({role})")
            lines.append("")

        if facts:
            lines.append("Material Facts:")
            for i, f in enumerate(facts, 1):
                src = f" (source: {f.provenance})" if f.provenance else ""
                lines.append(f"  {i}. {f.text}{src}")
            lines.append("")

        if timeline:
            lines.append("Chronology:")
            for e in timeline:
                when = e.when.strftime("%Y-%m-%d %H:%M") if e.when else "Undated"
                lines.append(f"  - [{when}] {e.description}")
            lines.append("")

        lines.append("Provisions Relied Upon:")
        for section_prov in provisions:
            if section_prov.section_id:
                lines.append(f"  - Section {section_prov.section_id}")
        lines.append("")

        if key in ("BAIL_APPLICATION", "AFFIDAVIT"):
            when = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            lines.append(f"Signed this {when}.")
        return "\n".join(lines)

    async def list_for_case(
        self, session: AsyncSession, *, case_id: int, owner_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[CasePleading], int]:
        await self._get_scoped_case(session, case_id, owner_id)
        total = int(
            (
                await session.execute(
                    select(func.count()).select_from(CasePleading).where(CasePleading.case_id == case_id)
                )
            ).scalar_one()
        )
        items = list(
            (
                await session.execute(
                    select(CasePleading)
                    .where(CasePleading.case_id == case_id)
                    .order_by(CasePleading.updated_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return items, total
