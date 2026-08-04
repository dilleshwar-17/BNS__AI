"""Drafting router (Phase 8). Matches docs/drafting.md + api.md contract."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.drafting.engine import DRAFT_TYPES, get_draft_type, list_draft_types
from app.drafting.service import DraftingService
from app.models.user import User
from app.schemas.drafting import (
    DraftGenerateRequest,
    DraftGenerateResponse,
    DraftTypeSchema,
    DraftTypesResponse,
)

router = APIRouter()


@router.get("/types", response_model=DraftTypesResponse, summary="List draft types")
async def list_types() -> DraftTypesResponse:
    return DraftTypesResponse(draft_types=[DraftTypeSchema.model_validate(t) for t in list_draft_types()])


@router.get("/templates/{draft_type}", response_model=DraftTypeSchema, summary="Get draft template")
async def get_template(
    draft_type: str,
    current_user: User = Depends(get_current_user),
) -> DraftTypeSchema:
    if draft_type not in DRAFT_TYPES:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("Draft type not found.")
    template = get_draft_type(draft_type)
    return DraftTypeSchema.model_validate(template)


@router.post("/generate", response_model=DraftGenerateResponse, summary="Generate a draft")
async def generate_draft(
    payload: DraftGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftGenerateResponse:
    service = DraftingService()
    result = service.generate(payload.draft_type, payload.answers)
    await audit_service.record(
        session,
        action="drafting.generate",
        request_id=get_request_id(),
        user_id=current_user.id,
        resource_type="draft",
        resource_id=payload.draft_type,
    )
    await session.commit()
    citations = [f"S.{e.section_id}" for e in result.evidence if e.section_id and e.section_id.isdigit()]
    return DraftGenerateResponse(
        draft_type=result.draft_type,
        content=result.content,
        grounded=result.grounded,
        citations=citations,
    )
