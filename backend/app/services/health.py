"""Health check service with real dependency probes.

Per spec section 86: readiness must genuinely test each dependency and must
never fail the whole endpoint because one dependency is unavailable.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_engine
from app.schemas.health import DependencyHealth

logger = get_logger(__name__)

Probe = Callable[[], Awaitable[None]]


class HealthChecker:
    """Runs dependency probes with per-check timeouts."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def _probe(self, name: str, probe: Probe) -> tuple[str, DependencyHealth]:
        start = time.perf_counter()
        try:
            await asyncio.wait_for(probe(), timeout=self.timeout_seconds)
            latency = (time.perf_counter() - start) * 1000
            return name, DependencyHealth(status="ok", latency_ms=round(latency, 2))
        except Exception as exc:  # noqa: BLE001 - probe boundary
            latency = (time.perf_counter() - start) * 1000
            logger.warning("dependency_health_error", dependency=name, error=str(exc))
            return name, DependencyHealth(status="error", latency_ms=round(latency, 2), error=str(exc)[:200])

    async def check_all(self, names: list[str] | None = None) -> dict[str, DependencyHealth]:
        probes = self._build_probes()
        if names is not None:
            probes = {name: fn for name, fn in probes.items() if name in names}
        results = await asyncio.gather(*(self._probe(name, fn) for name, fn in probes.items()))
        return dict(results)

    def _build_probes(self) -> dict[str, Probe]:
        return {
            "postgres": self._check_postgres,
            "redis": self._check_redis,
            "chroma": self._check_chroma,
            "neo4j": self._check_neo4j,
            "ollama": self._check_ollama,
        }

    async def _check_postgres(self) -> None:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def _check_redis(self) -> None:
        import redis.asyncio as redis

        settings = get_settings()
        client = redis.from_url(settings.redis_url)
        try:
            await client.ping()
        finally:
            close = getattr(client, "aclose", None)
            if close is not None:
                await close()
            else:
                await client.close()

    async def _check_chroma(self) -> None:
        settings = get_settings()
        url = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat"
        headers: dict[str, Any] = {}
        if settings.chroma_token:
            headers["X-Chroma-Token"] = settings.chroma_token
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

    async def _check_neo4j(self) -> None:
        from neo4j import GraphDatabase

        settings = get_settings()
        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        try:
            await asyncio.to_thread(self._neo4j_ping, driver)
        finally:
            await asyncio.to_thread(driver.close)

    @staticmethod
    def _neo4j_ping(driver) -> None:
        with driver.session() as session:
            session.run("RETURN 1").consume()

    async def _check_ollama(self) -> None:
        settings = get_settings()
        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(url)
            resp.raise_for_status()


health_checker = HealthChecker()
