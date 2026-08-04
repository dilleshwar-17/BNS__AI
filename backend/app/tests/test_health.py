"""Health endpoint tests."""

from __future__ import annotations

from app.schemas.health import DependencyHealth
from app.services.health import health_checker
from httpx import AsyncClient


async def test_liveness(client: AsyncClient) -> None:
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "live"
    assert "checks" in body


async def test_readiness_ok(client: AsyncClient, monkeypatch) -> None:
    async def fake_check_all(names=None) -> dict[str, DependencyHealth]:
        return {
            name: DependencyHealth(status="ok", latency_ms=1.0) for name in ("postgres", "redis", "chroma", "neo4j")
        }

    monkeypatch.setattr(health_checker, "check_all", fake_check_all)
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


async def test_readiness_degraded(client: AsyncClient, monkeypatch) -> None:
    async def fake_check_all(names=None) -> dict[str, DependencyHealth]:
        checks = {
            "postgres": DependencyHealth(status="ok", latency_ms=1.0),
            "redis": DependencyHealth(status="ok", latency_ms=1.0),
            "chroma": DependencyHealth(status="ok", latency_ms=1.0),
            "neo4j": DependencyHealth(status="error", latency_ms=1.0, error="boom"),
        }
        return checks

    monkeypatch.setattr(health_checker, "check_all", fake_check_all)
    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["status"] == "unavailable"


async def test_legacy_health_alias(client: AsyncClient, monkeypatch) -> None:
    async def fake_check_all(names=None) -> dict[str, DependencyHealth]:
        return {
            name: DependencyHealth(status="ok", latency_ms=1.0) for name in ("postgres", "redis", "chroma", "neo4j")
        }

    monkeypatch.setattr(health_checker, "check_all", fake_check_all)
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
