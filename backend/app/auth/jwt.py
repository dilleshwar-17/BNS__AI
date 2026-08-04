"""JWT creation and verification for access and refresh tokens.

Access tokens are short-lived (self-contained). Refresh tokens carry a ``jti``
that maps to a stored, revocable ``auth_sessions`` row; we never trust a refresh
token unless the matching session is present and unrevoked.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import get_settings


class TokenService:
    """Creates and validates JWTs using the configured secret/algorithm."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def create_access_token(self, user_id: str, role: str, username: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role.lower(),
            "username": username,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.settings.access_token_expire_minutes),
        }
        return jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.jwt_algorithm)

    def create_refresh_token(self, user_id: str, session_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "jti": str(session_id),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.settings.refresh_token_expire_days),
        }
        return jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.jwt_algorithm)

    def decode_token(self, token: str, expected_type: str) -> dict | None:
        """Decode + validate a token. Returns payload or None if invalid/expired."""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
        except JWTError:
            return None
        if payload.get("type") != expected_type:
            return None
        return payload

    def hash_refresh_token(self, token: str) -> str:
        """Hash a refresh token for storage (SHA-256 of its canonical string)."""
        import hashlib

        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())


token_service = TokenService()
