"""Health check schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

DependencyStatus = Literal["ok", "error"]


class DependencyHealth(BaseModel):
    status: DependencyStatus
    latency_ms: float
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["live", "ready", "degraded", "unavailable"]
    request_id: str | None = None
    checks: dict[str, DependencyHealth]
