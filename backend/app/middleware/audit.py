import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_var

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        user = "anonymous"
        if hasattr(request.state, "user_id"):
            user = request.state.user_id

        logger.info(
            "request",
            request_id=getattr(request.state, "request_id", None),
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=f"{duration:.3f}s",
            user=user,
        )

        # Write to immutable audit log for important actions
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and response.status_code < 500:
            try:
                import uuid

                from app.database.models.audit_log import AuditLog
                from app.database.session import async_session_factory

                async with async_session_factory() as session:
                    log_entry = AuditLog(
                        id=str(uuid.uuid4()),
                        user_id=user if user != "anonymous" else None,
                        action=f"{request.method}:{request.url.path}",
                        resource=request.url.path.split("/")[3] if len(request.url.path.split("/")) > 3 else "unknown",
                        resource_id=request.url.path.split("/")[-1] if request.url.path.split("/")[-1] else None,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent", "")[:500],
                        request_id=request_id_var.get(),
                        status_code=response.status_code,
                        duration_ms=round(duration * 1000, 2),
                    )
                    session.add(log_entry)
                    await session.commit()
            except Exception:
                pass  # Never block the request on audit failure

        return response
