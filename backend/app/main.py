"""FastAPI application factory and lifespan."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import BNSAIError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.request_id import get_request_id
from app.db.session import close_engine

logger = get_logger(__name__)


def _error_response(code: str, message: str, status_code: int, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "error": {
                "code": code,
                "message": message,
                "request_id": get_request_id() or None,
                "details": details,
            },
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    logger.info(
        "application_startup",
        environment=settings.environment,
        app_version=settings.app_version,
    )
    yield
    await close_engine()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Retrieval-first, agentic RAG backend for BNS legal intelligence.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- Middleware (last added runs first) --------------------------------
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routes ------------------------------------------------------------
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_prefix)

    # Legacy /api/v1/health alias for frontend compatibility.
    legacy_health = APIRouter(tags=["health"])

    @legacy_health.get("/health")
    async def legacy_health_endpoint() -> JSONResponse:
        return await health.health_ready()

    app.include_router(legacy_health, prefix=settings.api_prefix)

    # --- Exception handlers ------------------------------------------------
    @app.exception_handler(BNSAIError)
    async def bnsai_error_handler(request: Request, exc: BNSAIError) -> JSONResponse:
        return _error_response(exc.code, exc.message, exc.http_status, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            "INVALID_REQUEST",
            "The request payload is invalid.",
            422,
            {"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            "HTTP_ERROR",
            str(exc.detail) if exc.detail else "HTTP error",
            exc.status_code,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("database_error", request_id=get_request_id())
        return _error_response(
            "INTERNAL_ERROR",
            "A database error occurred.",
            500,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", request_id=get_request_id())
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
            500,
        )

    return app


app = create_app()
