"""Phase 18: case intelligence service tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from app.core.exceptions import NotFoundError
from app.models.case import (
    CandidateProvision,
    Case,
    CaseContradiction,
    CaseEvidence,
    CaseFollowUp,
    CaseMissingFact,
    CaseVersion,
)
from app.models.user import User
from app.services.case import CaseService
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


async def _make_case(db_session, *, title: str = "State v. Iyer") -> tuple[User, Case]:
    user = await _make_user(db_session)
    svc = CaseService()
    case = await svc.create_case(
        db_session,
        user_id=user.id,
        title=title,
        description="A theft matter",
        matter_number=None,
        court="SDJM",
    )
    await db_session.commit()
    return user, case


# -- crud ---------------------------------------------------------------


async def test_create_case(db_session) -> None:
    user = await _make_user(db_session)
    svc = CaseService()
    case = await svc.create_case(
        db_session,
        user_id=user.id,
        title="State v. Iyer",
        description="Theft",
        matter_number="T-77/2026",
        court="SDJM",
    )
    await db_session.commit()
    assert case.id
    assert case.status == "OPEN"
    await db_session.refresh(case)
    assert case.title == "State v. Iyer"
    assert case.matter_number == "T-77/2026"


async def test_list_and_count_cases(db_session) -> None:
    owner, _ = await _make_case(db_session)
    other = await _make_user(db_session)
    svc = CaseService()
    await svc.create_case(
        db_session, user_id=owner.id, title="Matter A", description=None, matter_number=None, court=None
    )
    await svc.create_case(
        db_session, user_id=owner.id, title="Matter B", description=None, matter_number=None, court=None
    )
    await db_session.commit()

    assert await svc.count_cases(db_session, owner.id) == 3
    assert await svc.count_cases(db_session, other.id) == 0
    cases = await svc.list_cases(db_session, owner.id, limit=10, offset=0)
    assert sorted(c.title for c in cases) == ["Matter A", "Matter B", "State v. Iyer"]


async def test_get_case_owner_scoped(db_session) -> None:
    owner, case = await _make_case(db_session)
    stranger = await _make_user(db_session)
    svc = CaseService()
    fetched = await svc.get_case(db_session, case.id, owner.id)
    assert fetched.id == case.id
    with pytest.raises(NotFoundError):
        await svc.get_case(db_session, case.id, stranger.id)


async def test_get_case_missing(db_session) -> None:
    owner = await _make_user(db_session)
    svc = CaseService()
    with pytest.raises(NotFoundError):
        await svc.get_case(db_session, 99999, owner.id)


# -- sub-records ----------------------------------------------------------


async def test_add_and_list_member(db_session) -> None:
    _, case = await _make_case(db_session)
    colleague = await _make_user(db_session)
    svc = CaseService()
    await svc.add_member(db_session, case_id=case.id, user_id=colleague.id, role_in_case="counsel")
    await db_session.commit()
    members = await svc.list_members(db_session, case.id)
    assert any(m.user_id == colleague.id for m in members)


async def test_add_and_list_party(db_session) -> None:
    _, case = await _make_case(db_session)
    svc = CaseService()
    party = await svc.add_party(db_session, case_id=case.id, name="Ravi Iyer", side="defence", is_claimant=False)
    await db_session.commit()
    parties = await svc.list_parties(db_session, case.id)
    assert parties[0].name == "Ravi Iyer"
    assert party.is_claimant is False


async def test_add_and_list_fact(db_session) -> None:
    _, case = await _make_case(db_session)
    svc = CaseService()
    fact = await svc.add_fact(db_session, case_id=case.id, text="Took the cycle", provenance="FIR", confidence=0.9)
    await db_session.commit()
    facts = await svc.list_facts(db_session, case.id)
    assert facts[0].text == "Took the cycle"
    assert facts[0].status == "accepted"
    assert fact.confidence == 0.9


async def test_add_and_list_timeline(db_session) -> None:
    _, case = await _make_case(db_session)
    svc = CaseService()
    when = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await svc.add_timeline_event(db_session, case_id=case.id, when=when, description="Theft occurred")
    await db_session.commit()
    events = await svc.list_timeline(db_session, case.id)
    assert len(events) == 1
    assert events[0].description == "Theft occurred"


# -- versioning ------------------------------------------------------------


async def test_snapshot_version_increments(db_session) -> None:
    _, case = await _make_case(db_session)
    svc = CaseService()
    await svc.add_fact(db_session, case_id=case.id, text="fact one", provenance=None, confidence=None)
    v1 = await svc.snapshot_version(db_session, case_id=case.id, note="v1")
    v2 = await svc.snapshot_version(db_session, case_id=case.id, note="v2")
    await db_session.commit()
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v2.snapshot == {"facts": ["fact one"]}


async def test_snapshot_defaults_to_one(db_session) -> None:
    _, case = await _make_case(db_session)
    svc = CaseService()
    v = await svc.snapshot_version(db_session, case_id=case.id)
    await db_session.commit()
    assert v.version_number == 1
    assert isinstance(v.snapshot, dict)


# -- derived entities are plain insertable ---------------------------------


async def test_can_create_sub_entities(db_session) -> None:
    _, case = await _make_case(db_session)
    evidence = CaseEvidence(case_id=case.id, document_id=uuid.uuid4(), description="doc")
    contradiction = CaseContradiction(case_id=case.id, fact_a_id=None, fact_b_id=None, summary="conflict")
    missing = CaseMissingFact(case_id=case.id, what="motive not established")
    provision = CandidateProvision(case_id=case.id, section_id="303", source_chunk_id=uuid.uuid4(), snippet="...")
    follow_up = CaseFollowUp(case_id=case.id, action="call witness")
    db_session.add_all([evidence, contradiction, missing, provision, follow_up])
    await db_session.commit()

    assert (
        await db_session.execute(select(CaseEvidence).where(CaseEvidence.case_id == case.id))
    ).scalar_one().document_id is not None
    assert (
        await db_session.execute(select(CaseContradiction).where(CaseContradiction.case_id == case.id))
    ).scalar_one().summary == "conflict"
    assert (
        await db_session.execute(select(CaseMissingFact).where(CaseMissingFact.case_id == case.id))
    ).scalar_one().what == "motive not established"
    assert (
        await db_session.execute(select(CaseVersion).where(CaseVersion.case_id == case.id))
    ).scalar_one_or_none() is None
