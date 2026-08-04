"""Legal research router (Phase 16). Matches plan contract:
/research/sessions, /research/runs, /research/reports/{id}.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.research import ResearchReport, ResearchRun, ResearchSession
from app.models.user import User
from app.schemas.research import (
    ResearchReportRead,
    ResearchRunList,
    ResearchRunRead,
    ResearchSessionCreate,
    ResearchSessionList,
    ResearchSessionRead,
    ResearchTriggerRequest,
)
from app.services.research import ResearchService

router = APIRouter()
service = ResearchService()


async def _get_session_or_404(session: AsyncSession, session_id: int, user_id) -> ResearchSession:
    rs = (
        await session.execute(
            select(ResearchSession).where(ResearchSession.id == session_id, ResearchSession.user_id == user_id)
        )
    ).scalar_one_or_none()
    if rs is None:
        raise NotFoundError("Research session not found.")
    return rs


@router.post("/sessions", response_model=ResearchSessionRead, status_code=201, summary="Create a research session")
async def create_session(
    payload: ResearchSessionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchSession:
    rs = await service.create_session(session, user_id=current_user.id, title=payload.title, topic=payload.topic)
    await audit_service.record(
        session,
        action="research.create",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="research_session",
        resource_id=str(rs.id),
    )
    await session.commit()
    await session.refresh(rs)
    return rs


@router.get("/sessions", response_model=ResearchSessionList, summary="List my research sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchSessionList:
    sessions = await service.list_sessions(session, current_user.id)
    return ResearchSessionList(sessions=[ResearchSessionRead.model_validate(rs) for rs in sessions])


@router.post("/runs", response_model=ResearchRunRead, summary="Run research on a session")
async def run_research(
    payload: ResearchTriggerRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchRun:
    rs = await _get_session_or_404(session, payload.session_id, current_user.id)
    run = await service.create_run(session, session_id=rs.id)
    # topic for the run comes from the session it belongs to
    run = await service.run_research(session, run=run, topic=rs.topic)
    await audit_service.record(
        session,
        action="research.run",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="research_run",
        resource_id=str(run.id),
    )
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/runs", response_model=ResearchRunList, summary="List runs for a session")
async def list_runs(
    session_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchRunList:
    await _get_session_or_404(session, session_id, current_user.id)
    runs = list(
        (
            await session.execute(
                select(ResearchRun).where(ResearchRun.session_id == session_id).order_by(ResearchRun.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ResearchRunList(runs=[ResearchRunRead.model_validate(r) for r in runs])


@router.get("/reports/{report_id}", response_model=ResearchReportRead, summary="Get a research report")
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ResearchReport:
    report = (await session.execute(select(ResearchReport).where(ResearchReport.id == report_id))).scalar_one_or_none()
    if report is None:
        raise NotFoundError("Report not found.")
    return report
