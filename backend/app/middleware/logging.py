import time

from fastapi import Request

from app.logging import get_logger

logger = get_logger(__name__)


async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration=round(duration, 3),
    )
    return response
