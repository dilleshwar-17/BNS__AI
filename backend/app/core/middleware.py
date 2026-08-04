"""ASGI middleware: request IDs, request logging, and security headers."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.request_id import get_request_id, request_id_scope

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign and propagate a request ID for every request."""

    def __init__(self, app, header: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header = header

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(self.header)
        async with request_id_scope(request_id) as rid:
            request.state.request_id = rid
            response = await call_next(request)
            response.headers[self.header] = rid
            return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log each request with method, path, status, duration, and request ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", get_request_id())
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline security headers to every response."""

    HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "X-XSS-Protection": "1; mode=block",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for header, value in self.HEADERS.items():
            response.headers.setdefault(header, value)
        settings = get_settings()
        if settings.is_production and "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            )
        return response
