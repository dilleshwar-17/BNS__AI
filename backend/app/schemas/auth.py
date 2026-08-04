"""User and auth schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, '_' and '-'")
        return v.strip()


class UserLogin(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Public user profile (matches the frontend contract)."""

    id: uuid.UUID
    email: EmailStr
    username: str
    full_name: str | None = None
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: datetime | None = None

    @field_validator("role")
    @classmethod
    def _lower_role(cls, v: str) -> str:
        return v.lower()

    model_config = {"from_attributes": True}
