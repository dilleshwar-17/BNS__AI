"""Case report generation service (Phase 20).

Aggregates a case's facts, parties, timeline, contradictions, missing facts,
provisions, scenarios, follow-ups into a client-ready report. It is
retrieval-only: it summarises data already on the case and never invents legal
content. Generation fails closed if the case has no accepted facts.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientBNSEvidenceError, NotFoundError
from app.models.case import (
    AlternativeScenario,
    CandidateProvision,
    Case,
    CaseContradiction,
    CaseFact,
    CaseFollowUp,
    CaseMissingFact,
    CaseParty,
    CaseTimelineEvent,
    ElementOfOffence,
    OutcomeScenario,
)
from app.models.report import CaseReport

REPORT_TYPES: dict[str, dict[str, str]] = {
    "SITUATION_REPORT": {
        "title": "Situation Report",
        "description": "Executive summary of facts, evidence and next steps.",
    },
    "CLIENT_SUMMARY": {
        "title": "Client Summary",
        "description": "Plain-language status briefing for a client.",
    },
    "PRE_HEARING_BRIEF": {
        "title": "Pre-Hearing Brief",
        "description": "Prepared brief for a hearing with charges and issues.",
    },
}


class ReportService:
    """Owner-scoped generation of client-facing case reports."""

    async def _get_scoped_case(self, session: AsyncSession, case_id: int, owner_id: uuid.UUID) -> Case:
        result = await session.execute(select(Case).where(Case.id == case_id, Case.owner_id == owner_id))
        case = result.scalar_one_or_none()
        if case is None:
            raise NotFoundError("Case not found.")
        return case

    async def _rows(self, session: AsyncSession, model, case_id: int) -> list:
        return list(
            (await session.execute(select(model).where(model.case_id == case_id).order_by(model.id))).scalars().all()
        )

    async def generate(
        self, session: AsyncSession, *, case_id: int, owner_id: uuid.UUID, report_type: str
    ) -> CaseReport:
        key = report_type.upper()
        if key not in REPORT_TYPES:
            raise NotFoundError(f"Unsupported report type: {report_type}")

        case = await self._get_scoped_case(session, case_id, owner_id)
        facts = await self._rows(session, CaseFact, case.id)
        if not facts:
            raise InsufficientBNSEvidenceError("No accepted facts on the case. Add facts before generating a report.")

        parties = await self._rows(session, CaseParty, case.id)
        timeline = await self._rows(session, CaseTimelineEvent, case.id)
        contradictions = await self._rows(session, CaseContradiction, case.id)
        missing = await self._rows(session, CaseMissingFact, case.id)
        provisions = await self._rows(session, CandidateProvision, case.id)
        elements = await self._rows(session, ElementOfOffence, case.id)
        alt_scenarios = await self._rows(session, AlternativeScenario, case.id)
        outcomes = await self._rows(session, OutcomeScenario, case.id)
        follow_ups = await self._rows(session, CaseFollowUp, case.id)

        citations = [p.section_id for p in provisions if p.section_id]
        sections = self._build_sections(
            case,
            facts,
            parties,
            timeline,
            contradictions,
            missing,
            provisions,
            elements,
            alt_scenarios,
            outcomes,
            follow_ups,
        )
        title = REPORT_TYPES[key]["title"]
        content = self._render(key, sections)

        report = CaseReport(
            case_id=case.id,
            owner_id=owner_id,
            report_type=key,
            title=title,
            content=content,
            sections=sections,
            citations=citations,
        )
        session.add(report)
        await session.flush()
        return report

    def _build_sections(
        self,
        case: Case,
        facts: list[CaseFact],
        parties: list[CaseParty],
        timeline: list[CaseTimelineEvent],
        contradictions: list[CaseContradiction],
        missing: list[CaseMissingFact],
        provisions: list[CandidateProvision],
        elements: list[ElementOfOffence],
        alt_scenarios: list[AlternativeScenario],
        outcomes: list[OutcomeScenario],
        follow_ups: list[CaseFollowUp],
    ) -> list[dict]:
        sections: list[dict] = []

        sections.append(
            {
                "heading": "Overview",
                "body": (
                    f"Case '{case.title}' is {case.status.lower()}. "
                    f"{len(facts)} fact(s) recorded, {len(parties)} party/ies, "
                    f"{len(provisions)} provision candidate(s)."
                ),
            }
        )

        if parties:
            sections.append(
                {
                    "heading": "Parties",
                    "body": "\n".join(
                        f"- {p.name} ({'Complainant' if p.is_claimant else (p.side or 'Party')})" for p in parties
                    ),
                }
            )

        if facts:
            sections.append(
                {
                    "heading": "Material Facts",
                    "body": "\n".join(
                        f"- {f.text}{f' [source: {f.provenance}]' if f.provenance else ''}" for f in facts
                    ),
                }
            )

        if timeline:
            sections.append(
                {
                    "heading": "Chronology",
                    "body": "\n".join(
                        f"- {e.when.isoformat() if e.when else 'Undated'}: {e.description}"
                        for e in sorted(timeline, key=lambda e: (e.when is None, e.when))
                    ),
                }
            )

        if contradictions:
            sections.append(
                {
                    "heading": "Contradictions",
                    "body": "\n".join(f"- {c.summary or 'Unresolved conflict between facts.'}" for c in contradictions),
                }
            )

        if missing:
            sections.append(
                {
                    "heading": "Missing Facts",
                    "body": "\n".join(f"- {m.what}" for m in missing),
                }
            )

        if provisions:
            sections.append(
                {
                    "heading": "Provisions",
                    "body": "\n".join(f"- Section {p.section_id}" for p in provisions if p.section_id),
                }
            )

        if elements:
            lines = [
                f"- Section {e.section_id} '{e.element}': {'satisfied' if e.satisfied else 'not satisfied'}"
                for e in elements
            ]
            sections.append({"heading": "Elements of Offence", "body": "\n".join(lines)})

        if alt_scenarios:
            sections.append(
                {
                    "heading": "Alternative Scenarios",
                    "body": "\n".join(f"- {s.label}: {s.description or ''}" for s in alt_scenarios),
                }
            )

        if outcomes:
            sections.append(
                {
                    "heading": "Outcome Scenarios",
                    "body": "\n".join(f"- {o.label} ({o.likelihood or 'n/a'}): {o.reasoning or ''}" for o in outcomes),
                }
            )

        if follow_ups:
            sections.append(
                {
                    "heading": "Follow-Ups",
                    "body": "\n".join(f"- {f.action} [{'done' if f.done else 'pending'}]" for f in follow_ups),
                }
            )
        return sections

    def _render(self, key: str, sections: list[dict]) -> str:
        lines = [REPORT_TYPES[key]["title"].upper(), "=" * len(REPORT_TYPES[key]["title"]), ""]
        for s in sections:
            lines.append(s["heading"])
            lines.append("-" * len(s["heading"]))
            lines.append(s["body"])
            lines.append("")
        return "\n".join(lines)

    async def list_for_case(
        self, session: AsyncSession, *, case_id: int, owner_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[CaseReport], int]:
        await self._get_scoped_case(session, case_id, owner_id)
        total = int(
            (
                await session.execute(select(func.count()).select_from(CaseReport).where(CaseReport.case_id == case_id))
            ).scalar_one()
        )
        items = list(
            (
                await session.execute(
                    select(CaseReport)
                    .where(CaseReport.case_id == case_id)
                    .order_by(CaseReport.updated_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return items, total
