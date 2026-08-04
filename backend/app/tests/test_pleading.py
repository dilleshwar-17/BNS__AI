"""Phase 19: pleading generation service tests."""

from __future__ import annotations

import uuid

import pytest
from app.core.exceptions import InsufficientBNSEvidenceError, NotFoundError
from app.models.case import (
    CandidateProvision,
    Case,
    CaseFact,
    CaseParty,
)
from app.models.pleading import CasePleading
from app.models.user import User
from app.services.case import CaseService
from app.services.pleading import DOCUMENT_TYPES, PleadingsService
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


async def _create_case(db_session, owner_id: uuid.UUID, *, title: str = "State v. Iyer") -> Case:
    case_svc = CaseService()
    case = await case_svc.create_case(
        db_session, user_id=owner_id, title=title, description="Theft", matter_number=None, court="SDJM"
    )
    await db_session.commit()
    return case


async def _make_populated_case(db_session) -> tuple[User, Case]:
    owner = await _make_user(db_session)
    case = await _create_case(db_session, owner.id)
    db_session.add_all(
        [
            CaseFact(case_id=case.id, text="Took the bicycle without consent", provenance="FIR", confidence=0.9),
            CaseParty(case_id=case.id, name="Ravi Iyer", side="defence", is_claimant=False),
            CandidateProvision(case_id=case.id, section_id="304", source_chunk_id=uuid.uuid4(), snippet="..."),
        ]
    )
    await db_session.commit()
    return owner, case


async def _make_case_with_prov(db_session, owner_id: uuid.UUID, *, facts: bool) -> Case:
    case = await _create_case(db_session, owner_id, title="No {}".format("facts" if facts else "prov"))
    if facts:
        db_session.add(CaseFact(case_id=case.id, text="a fact", provenance=None, confidence=None))
    else:
        db_session.add(
            CandidateProvision(case_id=case.id, section_id="404", source_chunk_id=uuid.uuid4(), snippet="...")
        )
    await db_session.commit()
    return case


async def test_generate_grounded(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    svc = PleadingsService()
    pleading = await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="COMPLAINT")
    await db_session.commit()
    assert pleading.document_type == "COMPLAINT"
    assert pleading.grounded is True
    assert pleading.citations == ["304"]
    assert "Section 304" in pleading.content
    assert "Ravi Iyer" in pleading.content


async def test_document_type_is_normalized(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    svc = PleadingsService()
    pleading = await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="case_summary")
    assert pleading.document_type == "CASE_SUMMARY"
    assert pleading.title == DOCUMENT_TYPES["CASE_SUMMARY"]["title"]


async def test_fails_closed_without_provisions(db_session) -> None:
    owner = await _make_user(db_session)
    case = await _make_case_with_prov(db_session, owner.id, facts=True)
    svc = PleadingsService()
    with pytest.raises(InsufficientBNSEvidenceError):
        await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="AFFIDAVIT")


async def test_fails_closed_without_facts(db_session) -> None:
    owner = await _make_user(db_session)
    case = await _make_case_with_prov(db_session, owner.id, facts=False)
    svc = PleadingsService()
    with pytest.raises(InsufficientBNSEvidenceError):
        await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="BAIL_APPLICATION")


async def test_rejects_unknown_type(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    svc = PleadingsService()
    with pytest.raises(NotFoundError):
        await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="WILL")


async def test_owner_scoped_lookup(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    stranger = await _make_user(db_session)
    svc = PleadingsService()
    with pytest.raises(NotFoundError):
        await svc.generate(db_session, case_id=case.id, owner_id=stranger.id, document_type="COMPLAINT")


async def test_list_for_case(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    svc = PleadingsService()
    await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="AFFIDAVIT")
    await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="COMPLAINT")
    await db_session.commit()
    items, total = await svc.list_for_case(db_session, case_id=case.id, owner_id=owner.id, limit=10, offset=0)
    assert total == 2
    assert {i.document_type for i in items} == {"AFFIDAVIT", "COMPLAINT"}


async def test_list_scoped_excludes_other_owner(db_session) -> None:
    owner, case = await _make_populated_case(db_session)
    stranger = await _make_user(db_session)
    svc = PleadingsService()
    with pytest.raises(NotFoundError):
        await svc.list_for_case(db_session, case_id=case.id, owner_id=stranger.id, limit=10, offset=0)


async def test_document_types_registry() -> None:
    assert set(DOCUMENT_TYPES) == {"AFFIDAVIT", "COMPLAINT", "BAIL_APPLICATION", "CASE_SUMMARY"}


async def test_pleadings_are_retrieval_only(db_session) -> None:
    """Content references only the case's curated sections, never fabricated ones."""
    owner, case = await _make_populated_case(db_session)
    svc = PleadingsService()
    pleading = await svc.generate(db_session, case_id=case.id, owner_id=owner.id, document_type="BAIL_APPLICATION")
    stored = (await db_session.execute(select(CasePleading).where(CasePleading.id == pleading.id))).scalar_one()
    assert stored.grounded is True
    assert stored.citations == ["304"]
    assert all(isinstance(c, str) for c in stored.citations)
