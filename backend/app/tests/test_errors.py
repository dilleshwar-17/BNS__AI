"""Error contract tests."""

from __future__ import annotations

from app.main import app
from fastapi.exceptions import RequestValidationError
from httpx import AsyncClient
from starlette.requests import Request


async def test_method_not_allowed_contract(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/health")
    assert resp.status_code == 405
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "HTTP_ERROR"


async def test_not_found_contract(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "HTTP_ERROR"


async def test_validation_error_contract() -> None:
    handler = app.exception_handlers[RequestValidationError]
    request = Request(
        scope={
            "type": "http",
            "method": "POST",
            "path": "/api/v1/health",
            "headers": [],
            "query_string": b"",
        }
    )
    exc = RequestValidationError(errors=[{"loc": ("body", "message"), "msg": "field required", "type": "missing"}])
    resp = await handler(request, exc)  # type: ignore[misc]
    assert resp.status_code == 422
    import json

    body = json.loads(resp.body)
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["message"]
