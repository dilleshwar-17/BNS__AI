from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024  # 10MB
REQUEST_TIMEOUT_SECONDS = 120


class RequestLimitsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_BODY_SIZE:
                return Response(
                    content="Request body too large",
                    status_code=413,
                    headers={"Content-Type": "text/plain"},
                )

        import asyncio

        try:
            response = await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
            return response
        except asyncio.TimeoutError:
            logger.warning("request_timeout", path=request.url.path, method=request.method)
            return Response(
                content="Request timeout",
                status_code=504,
                headers={"Content-Type": "text/plain"},
            )
