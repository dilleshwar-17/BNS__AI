"""Request ID propagation via contextvars."""

from __future__ import annotations

import contextvars
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def get_request_id() -> str:
    return request_id_var.get() or ""


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)


@asynccontextmanager
async def request_id_scope(request_id: str | None = None) -> AsyncIterator[str]:
    """Provide a request id for the duration of the async context."""
    rid = request_id or generate_request_id()
    token = request_id_var.set(rid)
    try:
        yield rid
    finally:
        request_id_var.reset(token)
