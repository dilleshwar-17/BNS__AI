"""Auth dependencies: current-user resolution and RBAC permission checks."""

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import token_service
from app.auth.service import get_user_by_id
from app.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from app.db.session import get_db
from app.models.rbac import Permission, Role, role_permissions, user_roles
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer access token, fail closed."""
    if token is None:
        raise AuthenticationRequiredError()
    payload = token_service.decode_token(token, "access")
    if payload is None:
        raise AuthenticationRequiredError()
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationRequiredError()
    try:
        user = await get_user_by_id(session, uuid.UUID(user_id))
    except Exception:
        raise AuthenticationRequiredError()
    if not user.is_active:
        raise AuthenticationRequiredError()
    return user


async def _resolve_permissions(session: AsyncSession, user: User) -> set[str]:
    """Resolve the set of permission names granted to a user via their roles."""
    stmt = (
        select(Permission.name)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(Role, Role.id == role_permissions.c.role_id)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user.id)
    )
    result = await session.execute(stmt)
    return {name for (name,) in result.all()}


def require_roles(*roles: str):
    """Return a dependency that ensures the user has at least one allowed role."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role.upper() not in {r.upper() for r in roles} and not user.is_superuser:
            raise PermissionDeniedError()
        return user

    return _checker


def require_permission(permission: str):
    """Return a dependency ensuring the user holds the given permission.

    Superusers implicitly hold every permission.
    """

    async def _checker(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> User:
        if user.is_superuser:
            return user
        permissions = await _resolve_permissions(session, user)
        if permission not in permissions:
            raise PermissionDeniedError()
        return user

    return _checker
