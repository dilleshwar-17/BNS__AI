"""Phase 20: case report generation service tests."""

from __future__ import annotations

import uuid

import pytest
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
from app.models.user import User
from app.services.case import CaseService
from app.services.report import REPORT_TYPES, ReportService
from sqlalchemy import select


async def _make_user(db_session) -> User:
    user = User(
        email=f"u{uuid.uuid4()}@test.dev",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="x",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _make_case(db_session, owner_id: uuid.UUID) -> Case:
    case = await CaseService().create_case(
        db_session,
        user_id=owner_id,
        title="State v. Iyer",
        description="Theft",
        matter_number=None,
        court="SDJM",
    )
    await db_session.commit()
    return case


async def _make_populated_case(db_session) -> tuple[User, Case]:
    owner = await _make_user(db_session)
    case = await _make_case(db_session, owner.id)
    db_session.add_all(
        [
            CaseFact(case_id=case.id, text="Took the bicycle", provenance="FIR", confidence=0.9),
            CaseParty(case_id=case.id, name="Ravi Iyer", side="defence", is_claimant=False),
            CaseTimelineEvent(case_id=case.id, when=None, description="Offence occurred"),
            CandidateProvision(case_id=case.id, section_id="304", source_chunk_id=uuid.uuid4(), snippet="..."),
            CaseFollowUp(case_id=case.id, action="call witness"),
        ]
    )
    await db_session.commit()
    return owner, case


async def _make_report(db_session, owner: User, case: Case) -> CaseReport:
    svc = ReportService()
    report = await svc.generate(db_session, case_id=case.id, owner_id=owner.id, report_type="CLIENT_SUMMARY")
    await db_session.commit()
    return report


async def test_generate_report_aggregates(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    report = await _make_report(db_session, owner, case)
    assert report.report_type == "CLIENT_SUMMARY"
    assert "Took the bicycle" in report.content
    assert "Section 304" in report.content
    assert "Ravi Iyer" in report.content
    assert "Offence occurred" in report.content or "The bicycle occurred" in report.content


async def test_report_captures_citations(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    report = await _make_report(db_session, owner, case)
    assert report.citations == ["304"]


async def test_report_type_normalized(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    svc = ReportService()
    report = await svc.generate(db_session, case_id=case.id, owner_id=owner.id, report_type="situation_report")
    assert report.report_type == "SITUATION_REPORT"


async def test_fails_closed_without_facts(db_session) -> None:
    owner = await _make_user(db_session)
    case = await _make_case(db_session, owner.id)
    svc = ReportService()
    with pytest.raises(InsufficientBNSEvidenceError):
        await svc.generate(db_session, case_id=case.id, owner_id=owner.id, report_type="CLIENT_SUMMARY")


async def test_rejects_unknown_type(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    svc = ReportService()
    with pytest.raises(NotFoundError):
        await svc.generate(db_session, case_id=case.id, owner_id=owner.id, report_type="MYSTERY")


async def test_owner_scoped_lookup(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    stranger = await _make_user(db_session)
    svc = ReportService()
    with pytest.raises(NotFoundError):
        await svc.generate(db_session, case_id=case.id, owner_id=stranger.id, report_type="CLIENT_SUMMARY")


async def test_report_uses_case_contradictions(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    db_session.add(CaseContradiction(case_id=case.id, fact_a_id=None, fact_b_id=None, summary="conflicting timelines"))
    await db_session.commit()
    report = await _make_report(db_session, owner, case)
    assert "conflicting timelines" in report.content


async def test_report_uses_missing_and_scenarios(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    (
        db_session.add_all(
            [
                CaseMissingFact(case_id=case.id, what="motive unknown", importance=None),
                AlternativeScenario(case_id=case.id, label="Accident", description="not theft"),
                OutcomeScenario(case_id=case.id, label="Acquittal", likelihood="low", reasoning="?"),
                ElementOfOffence(case_id=case.id, section_id="304", element="intent", satisfied=True, note=None),
            ]
        ),
    )
    await db_session.commit()
    report = await _make_report(db_session, owner, case)
    assert "motive unknown" in report.content
    assert "Accident" in report.content
    assert "Acquittal" in report.content
    assert "intention" in report.content or "intent" in report.content


async def test_list_for_case(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    await _make_report(db_session, owner, case)
    await _make_report(db_session, owner, case)
    svc = ReportService()
    items, total = await svc.list_for_case(db_session, case_id=case.id, owner_id=owner.id, limit=10, offset=0)
    assert total == 2
    assert len(items) == 2


async def test_list_scoped_excludes_other_owner(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    stranger = await _make_user(db_session)
    svc = ReportService()
    with pytest.raises(NotFoundError):
        await svc.list_for_case(db_session, case_id=case.id, owner_id=stranger.id, limit=10, offset=0)


async def test_report_types_registry() -> None:
    assert set(REPORT_TYPES) == {"SITUATION_REPORT", "CLIENT_SUMMARY", "PRE_HEARING_BRIEF"}


async def test_report_persists_sections(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    report = await _make_report(db_session, owner, case)
    stored = (await db_session.execute(select(CaseReport).where(CaseReport.id == report.id))).scalar_one()
    assert isinstance(stored.sections, list)
    assert all("heading" in s and "body" in s for s in stored.sections)
