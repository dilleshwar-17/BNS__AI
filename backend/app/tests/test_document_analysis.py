"""Phase 17: document analysis service tests."""

from __future__ import annotations

import uuid

from app.models.analysis import (
    ANALYSIS_COMPLETED,
    ANALYSIS_FAILED,
    DocumentAnalysis,
)
from app.models.user import User
from app.retrieval.hybrid import RetrievalResult
from app.retrieval.service import RetrievalOutcome, RetrievalService
from app.services.document_analysis import DocumentAnalysisService


class _FakeRetrieval(RetrievalService):
    def __init__(self, hits: list[str]) -> None:
        super().__init__()
        self._hits = hits

    def retrieve(self, query, *, top_k=None, where=None, fail_closed=False):
        results = [
            RetrievalResult(
                chunk_id=uuid.uuid4(),
                text=f"Section {i} provision.",
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


def _detect_issues(service: DocumentAnalysisService, text: str) -> list[str]:
    return service._detect_issues(text)


def test_detect_issues_finds_offences() -> None:
    svc = DocumentAnalysisService(retrieval=_FakeRetrieval([]))
    issues = _detect_issues(svc, "The accused committed theft and later an assault.")
    assert "theft" in issues and "assault" in issues


def test_detect_issues_dedupes() -> None:
    svc = DocumentAnalysisService(retrieval=_FakeRetrieval([]))
    issues = _detect_issues(svc, "theft of a car then theft of a bike")
    assert issues.count("theft") == 1


def test_detect_issues_empty() -> None:
    svc = DocumentAnalysisService(retrieval=_FakeRetrieval([]))
    assert _detect_issues(svc, "no legal content here") == []


async def test_analyze_completed_and_grounded(db_session) -> None:
    svc = DocumentAnalysisService(retrieval=_FakeRetrieval(["112", "44"]))
    user = await _make_user(db_session)
    a = DocumentAnalysis(
        user_id=user.id,
        document_id=uuid.uuid4(),
        status="PENDING",
        document_text="He committed theft and then assaulted her.",
        grounded=False,
    )
    db_session.add(a)
    await db_session.commit()
    await svc.analyze(db_session, analysis=a)
    await db_session.commit()

    assert a.status == ANALYSIS_COMPLETED
    assert a.grounded is True
    assert a.issues
    assert "theft" in [m["issue"] for m in a.issues]
    assert "Legal Analysis" in (a.report or "")


async def test_analyze_fails_closed_empty(db_session) -> None:
    svc = DocumentAnalysisService(retrieval=_FakeRetrieval([]))
    user = await _make_user(db_session)
    a = DocumentAnalysis(
        user_id=user.id,
        document_id=uuid.uuid4(),
        status="PENDING",
        document_text="   ",
        grounded=False,
    )
    db_session.add(a)
    await db_session.commit()
    await svc.analyze(db_session, analysis=a)
    assert a.status == ANALYSIS_FAILED
    assert a.note == "empty_document"


async def test_analyze_no_issues(db_session) -> None:
    svc = DocumentAnalysisService(retrieval=_FakeRetrieval([]))
    user = await _make_user(db_session)
    a = DocumentAnalysis(
        user_id=user.id,
        document_id=uuid.uuid4(),
        status="PENDING",
        document_text="hello world nothing here",
        grounded=False,
    )
    db_session.add(a)
    await db_session.commit()
    await svc.analyze(db_session, analysis=a)
    assert a.status == ANALYSIS_FAILED
    assert a.note == "no_legal_issues_detected"


async def _make_user(db_session) -> User:
    user = User(
        email=f"u{uuid.uuid4()}@test.dev",
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="x",
    )
    db_session.add(user)
    await db_session.commit()
    return user
