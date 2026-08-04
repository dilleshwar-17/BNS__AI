"""Auth router: register, login, refresh, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit_service
from app.auth.dependencies import get_current_user
from app.auth.service import (
    authenticate,
    create_session_pair,
    logout,
    register_user,
    rotate_refresh,
)
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair, UserCreate, UserLogin, UserRead

router = APIRouter()


def _client_context(request: Request) -> dict[str, str | None]:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.post("/register", response_model=UserRead, status_code=201, summary="Register a new user")
async def register(payload: UserCreate, request: Request, session: AsyncSession = Depends(get_db)) -> User:
    user = await register_user(session, email=payload.email, username=payload.username, password=payload.password)
    await audit_service.record(
        session,
        action="auth.register",
        request_id=get_request_id(),
        user_id=user.id,
        resource_type="user",
        metadata={"ip": _client_context(request)["ip_address"]},
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenPair, summary="Login with username/password")
async def login(payload: UserLogin, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    user = await authenticate(session, username=payload.username, password=payload.password)
    ctx = _client_context(request)
    tokens = await create_session_pair(session, user, ip_address=ctx["ip_address"], user_agent=ctx["user_agent"])
    await audit_service.record(
        session,
        action="auth.login",
        request_id=get_request_id(),
        user_id=user.id,
        resource_type="user",
        metadata={"ip": ctx["ip_address"]},
    )
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair, summary="Rotate refresh token")
async def refresh(payload: RefreshRequest, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    ctx = _client_context(request)
    tokens = await rotate_refresh(
        session,
        payload.refresh_token,
        ip_address=ctx["ip_address"],
        user_agent=ctx["user_agent"],
    )
    await session.commit()
    return tokens


@router.post("/logout", status_code=200, summary="Revoke refresh token")
async def logout_endpoint(payload: RefreshRequest, session: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    await logout(session, payload.refresh_token)
    await session.commit()
    return {"success": True}


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def me(user: User = Depends(get_current_user)) -> User:
    return user
