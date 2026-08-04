"""Pleading router (Phase 19). Generates retrieval-only legal documents from a case.

GET  /pleadings/types                    - list supported document types
POST /pleadings/generate                 - generate a pleading for a case
GET  /pleadings/cases/{case_id}          - list generated pleadings for a case
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.user import User
from app.schemas.pleading import (
    PleadingGenerateRequest,
    PleadingList,
    PleadingRead,
    PleadingTypeSchema,
    PleadingTypesResponse,
)
from app.services.pleading import DOCUMENT_TYPES, PleadingsService

router = APIRouter()
service = PleadingsService()


@router.get("/types", response_model=PleadingTypesResponse, summary="List document types")
async def list_types() -> PleadingTypesResponse:
    return PleadingTypesResponse(
        document_types=[
            PleadingTypeSchema(name=name, title=meta["title"], description=meta["description"])
            for name, meta in DOCUMENT_TYPES.items()
        ]
    )


@router.post("/generate", response_model=PleadingRead, status_code=201, summary="Generate a pleading for a case")
async def generate(
    payload: PleadingGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PleadingRead:
    pleading = await service.generate(
        session,
        case_id=payload.case_id,
        owner_id=current_user.id,
        document_type=payload.document_type,
    )
    await audit_service.record(
        session,
        action="pleadings.generate",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="pleading",
        resource_id=f"{payload.case_id}:{pleading.document_type}",
    )
    await session.commit()
    await session.refresh(pleading)
    return PleadingRead.model_validate(pleading)


@router.get("/cases/{case_id}", response_model=PleadingList, summary="List pleadings for a case")
async def list_for_case(
    case_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PleadingList:
    items, total = await service.list_for_case(
        session, case_id=case_id, owner_id=current_user.id, limit=limit, offset=offset
    )
    return PleadingList(items=[PleadingRead.model_validate(p) for p in items], total=total)
