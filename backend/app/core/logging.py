import logging
import uuid
from contextvars import ContextVar
from typing import Optional

import structlog

from app.core.settings import get_settings

settings = get_settings()

# Context variable for request_id propagation across async calls
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestContextFilter(structlog.stdlib.Processor):
    """Injects request_id from context vars into every log entry."""

    def __call__(self, logger, method_name, event_dict):
        rid = request_id_var.get()
        if rid is not None:
            event_dict["request_id"] = rid
        return event_dict


_request_id_filter = RequestContextFilter()


def setup_logging() -> None:
    structlog.configure(
        processors=[
            _request_id_filter,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_request_id(request_id: Optional[str] = None) -> str:
    """Set request_id in context vars. Returns the bound id."""
    rid = request_id or str(uuid.uuid4())
    request_id_var.set(rid)
    return rid
