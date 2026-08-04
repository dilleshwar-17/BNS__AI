"""Health endpoints.

- ``GET /health/live``  — process liveness (always 200 when serving).
- ``GET /health/ready`` — readiness: real dependency checks; 200 only if all
  required dependencies are available, 503 otherwise.
- ``GET /api/v1/health`` — compatibility alias returning the same readiness info.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.request_id import get_request_id
from app.schemas.health import DependencyHealth, HealthResponse
from app.services.health import health_checker

router = APIRouter(tags=["health"])

# Dependencies that must be healthy for the API to serve meaningful requests.
REQUIRED_DEPENDENCIES = ("postgres", "redis", "chroma", "neo4j")


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness probe",
)
async def health_live() -> HealthResponse:
    return HealthResponse(
        status="live",
        request_id=get_request_id(),
        checks={name: DependencyHealth(status="ok", latency_ms=0.0) for name in REQUIRED_DEPENDENCIES},
    )


@router.get(
    "/health/ready",
    summary="Readiness probe (real dependency checks)",
    responses={503: {"model": HealthResponse}},
)
async def health_ready() -> JSONResponse:
    checks = await health_checker.check_all()
    ok = all(checks[name].status == "ok" for name in REQUIRED_DEPENDENCIES)
    overall: Literal["ready", "unavailable"] = "ready" if ok else "unavailable"
    response = HealthResponse(
        status=overall,
        request_id=get_request_id(),
        checks=checks,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=200 if ok else 503,
    )


@router.get(
    "/health",
    summary="Legacy health endpoint",
)
async def health_legacy() -> JSONResponse:
    return await health_ready()
