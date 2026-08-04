"""Authentication service: register, login, refresh with rotation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import token_service
from app.auth.password import hash_password, verify_password
from app.core.config import get_settings
from app.core.exceptions import (
    InvalidCredentialsError,
    NotFoundError,
    TokenExpiredError,
)
from app.models.auth_sessions import AuthSession
from app.models.user import User


async def _revoke_session(session: AsyncSession, auth_session: AuthSession, replaced_by: uuid.UUID | None) -> None:
    auth_session.revoked_at = datetime.now(timezone.utc)
    auth_session.replaced_by_id = replaced_by
    session.add(auth_session)


async def register_user(session: AsyncSession, *, email: str, username: str, password: str) -> User:
    user = User(
        email=email,
        username=username,
        password_hash=await hash_password(password),
        role="USER",
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.flush()
    return user


async def authenticate(session: AsyncSession, *, username: str, password: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not await verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InvalidCredentialsError()
    user.last_login_at = datetime.now(timezone.utc)
    await session.flush()
    return user


async def create_session_pair(
    session: AsyncSession, user: User, *, ip_address: str | None = None, user_agent: str | None = None
) -> dict[str, str]:
    settings = get_settings()
    session_id = token_service.new_session_id()
    access = token_service.create_access_token(str(user.id), user.role, user.username)
    refresh = token_service.create_refresh_token(str(user.id), session_id)

    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=token_service.hash_refresh_token(refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(auth_session)
    await session.flush()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


async def rotate_refresh(
    session: AsyncSession,
    refresh_token: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, str]:
    """Validate a refresh token, revoke it, and issue a fresh pair."""
    payload = token_service.decode_token(refresh_token, "refresh")
    if payload is None:
        raise TokenExpiredError()
    session_id = payload.get("jti")
    user_id = payload.get("sub")
    if not session_id or not user_id:
        raise TokenExpiredError()

    token_hash = token_service.hash_refresh_token(refresh_token)
    result = await session.execute(select(AuthSession).where(AuthSession.refresh_token_hash == token_hash))
    auth_session = result.scalar_one_or_none()
    if auth_session is None or auth_session.revoked_at is not None:
        raise TokenExpiredError()
    if auth_session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise TokenExpiredError()

    user_result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise TokenExpiredError()

    await _revoke_session(session, auth_session, replaced_by=None)
    await session.flush()

    new_session_id = token_service.new_session_id()
    access = token_service.create_access_token(str(user.id), user.role, user.username)
    new_refresh = token_service.create_refresh_token(str(user.id), new_session_id)
    new_auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=token_service.hash_refresh_token(new_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_expire_days),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(new_auth_session)
    await session.flush()
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer"}


async def logout(session: AsyncSession, refresh_token: str) -> None:
    """Revoke the given refresh token on explicit logout."""
    payload = token_service.decode_token(refresh_token, "refresh")
    if payload is None:
        return
    token_hash = token_service.hash_refresh_token(refresh_token)
    result = await session.execute(select(AuthSession).where(AuthSession.refresh_token_hash == token_hash))
    auth_session = result.scalar_one_or_none()
    if auth_session is not None:
        auth_session.revoked_at = datetime.now(timezone.utc)
        session.add(auth_session)
        await session.flush()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError()
    return user
