"""Phase 16: legal research service + planner tests."""

from __future__ import annotations

import uuid

from app.models.research import (
    RESEARCH_COMPLETED,
    RESEARCH_FAILED,
    ResearchReport,
)
from app.models.user import User
from app.retrieval.hybrid import RetrievalResult
from app.retrieval.service import RetrievalOutcome, RetrievalService
from app.services.research import ResearchService
from sqlalchemy import select


class _FakeRetrieval(RetrievalService):
    def __init__(self, hits: list[str]) -> None:
        super().__init__()
        self._hits = hits

    def retrieve(self, query, *, top_k=None, where=None, fail_closed=False):
        results = [
            RetrievalResult(
                chunk_id=uuid.uuid4(),
                text=f"Section {i} covers this.",
                score=0.9,
                metadata={
                    "section_id": str(i),
                    "section_title": f"Section {i}",
                    "element_type": "SECTION",
                },
            )
            for i in self._hits
        ]
        return RetrievalOutcome(results=results, query=query, top_k=len(results), gated=False)


def test_plan_decomposes_punishment() -> None:
    svc = ResearchService(retrieval=_FakeRetrieval([]))
    queries = svc.plan("punishment for theft")
    assert any("punishment" in q for q in queries)
    assert 0 < len(queries) <= 5


def test_plan_fallback() -> None:
    svc = ResearchService(retrieval=_FakeRetrieval([]))
    queries = svc.plan("fnord")
    assert len(queries) >= 1


def test_plan_empty() -> None:
    svc = ResearchService(retrieval=_FakeRetrieval([]))
    assert svc.plan("") == []


def test_plan_is_bounded() -> None:
    svc = ResearchService(retrieval=_FakeRetrieval([]))
    assert len(svc.plan("punishment for theft across many sections")) <= 5


def test_plan_strips_leading_intent() -> None:
    svc = ResearchService(retrieval=_FakeRetrieval([]))
    queries = svc.plan("punishment for theft")
    # no duplicated "punishment for punishment for theft"
    assert all("punishment for punishment" not in q for q in queries)
    assert any("theft" in q for q in queries)
    fallback = svc.plan("define murder")
    assert any("murder" in q for q in fallback)


async def test_produces_completed_report(db_session) -> None:
    svc = ResearchService(retrieval=_FakeRetrieval(["112", "44", "37"]))
    user = await _make_user(db_session)
    rs = await svc.create_session(db_session, user_id=user.id, title="t", topic="theft")
    run = await svc.create_run(db_session, session_id=rs.id)
    await svc.run_research(db_session, run=run, topic=rs.topic)
    await db_session.commit()

    assert run.status == RESEARCH_COMPLETED
    assert run.evidence_pool
    report = (await db_session.execute(select(ResearchReport).where(ResearchReport.run_id == run.id))).scalar_one()
    assert report.grounded is True
    assert "Research Report" in report.content


async def test_fails_closed_without_evidence(db_session) -> None:
    svc = ResearchService(retrieval=_FakeRetrieval([]))
    user = await _make_user(db_session)
    rs = await svc.create_session(db_session, user_id=user.id, title="t", topic="noise")
    run = await svc.create_run(db_session, session_id=rs.id)
    await svc.run_research(db_session, run=run, topic=rs.topic)
    await db_session.commit()

    assert run.status == RESEARCH_FAILED
    assert run.note == "insufficient_bns_evidence"
    assert not run.evidence_pool


async def _make_user(db_session) -> User:
    user = User(
        email=f"u{uuid.uuid4()}@test.dev",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="x",
    )
    db_session.add(user)
    await db_session.commit()
    return user
