"""Common response schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error contract (spec section 87 / 61)."""

    code: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class Meta(BaseModel):
    request_id: str


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: Meta
