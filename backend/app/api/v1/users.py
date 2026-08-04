"""Users router."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_roles
from app.core.constants import ROLE_USER
from app.models.user import User
from app.schemas.auth import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def me(user: User = Depends(require_roles(ROLE_USER))) -> User:
    return user
