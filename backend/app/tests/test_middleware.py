"""Middleware tests: request IDs and security headers."""

from __future__ import annotations

from httpx import AsyncClient


async def test_request_id_header(client: AsyncClient) -> None:
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")
    assert resp.headers["X-Request-ID"].startswith("req_")


async def test_security_headers_present(client: AsyncClient) -> None:
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
