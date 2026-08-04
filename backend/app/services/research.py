"""Legal research service (Phase 16).

A bounded, grounded research pipeline:
    1. Plan: split the research topic into sub-queries.
    2. Retrieve: evidence for each sub-query via the hybrid retriever.
    3. Aggregate: merge + dedupe into a bounded evidence pool.
    4. Synthesize: assemble a structured report from the evidence.

The pipeline is evidence-grounded and fail-closed: if no sub-query retrieves
verifiable BNS evidence, the run fails with no hallucinated content. Planning is
deterministic (LLM-free) so behaviour is reproducible and independent of model
availability.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.research import (
    RESEARCH_COMPLETED,
    RESEARCH_FAILED,
    RESEARCH_PENDING,
    RESEARCH_RUNNING,
    ResearchReport,
    ResearchRun,
    ResearchSession,
)
from app.retrieval.service import RetrievalService

_DECOMPOSERS: tuple[tuple[re.Pattern, list[str]], ...] = (
    (
        re.compile(r"\b(punishment|penalty|imprisonment|jail|fine)\b", re.I),
        [
            "what is the punishment for {t}",
            "imprisonment and fine for {t}",
            "sections prescribing punishment for {t}",
        ],
    ),
    (
        re.compile(r"\b(define|meaning|what is|what are)\b", re.I),
        [
            "define {t} under BNS",
            "what is the legal definition of {t}",
            "essential ingredients of {t}",
        ],
    ),
    (
        re.compile(r"\b(exception|but not|not an offence)\b", re.I),
        [
            "exceptions to {t}",
            "when is {t} not an offence",
            "exceptions and provisos for {t}",
        ],
    ),
    (
        re.compile(r"\b(bail|bailable|non-bailable)\b", re.I),
        [
            "grounds for bail in {t}",
            "is {t} bailable or non-bailable",
            "bail conditions for {t}",
        ],
    ),
    (
        re.compile(r"\b(procedure|cogniza?ble|trial|investigation)\b", re.I),
        [
            "procedural requirements for {t}",
            "is {t} cognizable",
            "investigation and trial for {t}",
        ],
    ),
    (
        re.compile(r"\b(offence|criminal)\b", re.I),
        [
            "what offence is {t}",
            "sections dealing with {t}",
            "related provisions for {t}",
        ],
    ),
)

_FALLBACK_TEMPLATES = [
    "BNS provisions for {t}",
    "what does the law say about {t}",
    "sections on {t}",
    "definition of {t}",
    "punishment related to {t}",
]


class ResearchService:
    """Bounded research orchestration over the retrieval layer."""

    def __init__(self, retrieval: RetrievalService | None = None) -> None:
        settings = get_settings()
        self._retriever = retrieval or RetrievalService()
        self._max_subqueries = settings.research_max_subqueries
        self._max_evidence = settings.research_max_evidence

    # -- persistence --------------------------------------------------------

    async def create_session(self, session: AsyncSession, *, user_id, title: str | None, topic: str) -> ResearchSession:
        rs = ResearchSession(user_id=user_id, title=title, topic=topic)
        session.add(rs)
        await session.flush()
        return rs

    async def create_run(self, session: AsyncSession, *, session_id: int) -> ResearchRun:
        run = ResearchRun(session_id=session_id, status=RESEARCH_PENDING)
        session.add(run)
        await session.flush()
        return run

    async def list_sessions(self, session: AsyncSession, user_id) -> list[ResearchSession]:
        return list(
            (
                await session.execute(
                    select(ResearchSession)
                    .where(ResearchSession.user_id == user_id)
                    .order_by(ResearchSession.updated_at.desc())
                )
            )
            .scalars()
            .all()
        )

    async def get_run_or_none(self, session: AsyncSession, run_id: int) -> ResearchRun | None:
        return (await session.execute(select(ResearchRun).where(ResearchRun.id == run_id))).scalar_one_or_none()

    # -- pipeline -----------------------------------------------------------

    def plan(self, topic: str) -> list[str]:
        t = (topic or "").strip()
        if not t:
            return []
        base = self._strip_sub(t)
        templates: list[str] = _FALLBACK_TEMPLATES
        for pattern, tpls in _DECOMPOSERS:
            if pattern.search(t):
                templates = tpls
                break
        queries: list[str] = []
        seen: set[str] = set()
        for tpl in templates:
            q = tpl.format(t=base)
            if q not in seen:
                seen.add(q)
                queries.append(q)
            if len(queries) >= self._max_subqueries:
                break
        return queries[: self._max_subqueries]

    @staticmethod
    def _strip_sub(topic: str) -> str:
        """Remove leading intent wrappers so templates read naturally."""
        return (
            re.sub(
                r"^(what is the |what are the |punishment for |the )|(offence of )",
                "",
                topic,
                flags=re.I,
            ).strip()
            or topic
        )

    def _retrieve(self, q: str) -> list[dict]:
        try:
            outcome = self._retriever.retrieve(q, fail_closed=False)
        except Exception:  # noqa: BLE001
            return []
        return [
            {
                "section_id": r.metadata.get("section_id"),
                "section_title": r.metadata.get("section_title"),
                "element_type": r.metadata.get("element_type"),
                "text": r.text,
                "score": round(r.score, 4),
            }
            for r in outcome.results
        ]

    async def run_research(self, session: AsyncSession, *, run: ResearchRun, topic: str) -> ResearchRun:
        run.status = RESEARCH_RUNNING
        await session.flush()

        subqueries = self.plan(topic)
        run.subqueries = subqueries

        pool: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for q in subqueries:
            for ev in self._retrieve(q):
                key = (str(ev.get("section_id")), str(ev.get("element_type")))
                if key in seen:
                    continue
                seen.add(key)
                pool.append(ev)
                if len(pool) >= self._max_evidence:
                    break
            if len(pool) >= self._max_evidence:
                break

        if not pool:
            run.status = RESEARCH_FAILED
            run.note = "insufficient_bns_evidence"
            await session.flush()
            return run

        run.evidence_pool = pool
        content = self._synthesize(topic, pool)
        report = ResearchReport(run_id=run.id, content=content, grounded=True, citations=pool)
        session.add(report)
        run.status = RESEARCH_COMPLETED
        await session.flush()
        return run

    def _synthesize(self, topic: str, pool: list[dict]) -> str:
        lines = [f"Research Report: {topic}\n"]
        for i, ev in enumerate(pool, start=1):
            sec = ev.get("section_id") or "n/a"
            lines.append(f"{i}. S.{sec} — {ev.get('section_title') or ''}")
            snippet = (ev.get("text") or "").strip()
            lines.append(f"   {snippet[:400]}")
        return "\n".join(lines)
