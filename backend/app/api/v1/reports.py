"""Case report router (Phase 20). Aggregates a case into a client-facing report.

GET /reports/types                - list supported report types
POST /reports/generate            - generate a report for a case
GET /reports/cases/{case_id}      - list generated reports for a case
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import (
    ReportGenerateRequest,
    ReportList,
    ReportRead,
    ReportTypeSchema,
    ReportTypesResponse,
)
from app.services.report import REPORT_TYPES, ReportService

router = APIRouter()
service = ReportService()


@router.get("/types", response_model=ReportTypesResponse, summary="List report types")
async def list_types() -> ReportTypesResponse:
    return ReportTypesResponse(
        report_types=[
            ReportTypeSchema(name=name, title=meta["title"], description=meta["description"])
            for name, meta in REPORT_TYPES.items()
        ]
    )


@router.post("/generate", response_model=ReportRead, status_code=201, summary="Generate a report for a case")
async def generate(
    payload: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReportRead:
    report = await service.generate(
        session,
        case_id=payload.case_id,
        owner_id=current_user.id,
        report_type=payload.report_type,
    )
    await audit_service.record(
        session,
        action="reports.generate",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="report",
        resource_id=f"{payload.case_id}:{report.report_type}",
    )
    await session.commit()
    await session.refresh(report)
    return ReportRead.model_validate(report)


@router.get("/cases/{case_id}", response_model=ReportList, summary="List reports for a case")
async def list_for_case(
    case_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReportList:
    items, total = await service.list_for_case(
        session, case_id=case_id, owner_id=current_user.id, limit=limit, offset=offset
    )
    return ReportList(items=[ReportRead.model_validate(r) for r in items], total=total)
