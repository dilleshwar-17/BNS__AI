import asyncio
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

OTEL_AVAILABLE = False
try:
    import opentelemetry

    OTEL_AVAILABLE = True
except ImportError:
    pass

from app.api.v1 import (
    admin,
    admin_prompts,
    auth,
    chat,
    dashboard,
    documents,
    drafting,
    health,
    ingestion,
    research,
    retrieval,
    upload,
    users,
)
from app.api.v1 import settings as user_settings
from app.core.events import event_bus
from app.core.logging import get_logger, setup_logging
from app.core.settings import get_settings
from app.database.base import Base
from app.database.session import engine
from app.graph.neo4j import close_driver
from app.integrations.ollama import close_http_clients
from app.middleware.audit import AuditMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_limits import RequestLimitsMiddleware

setup_logging()
logger = get_logger(__name__)
settings = get_settings()

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])
ACTIVE_CONNECTIONS = Gauge("active_connections", "Active WebSocket connections")
DB_QUERY_DURATION = Histogram("db_query_duration_seconds", "Database query duration", ["operation"])
LLM_REQUEST_COUNT = Counter("llm_requests_total", "Total LLM requests", ["provider", "status"])
LLM_LATENCY = Histogram("llm_request_duration_seconds", "LLM request latency", ["provider"])
VECTOR_SEARCH_DURATION = Histogram("vector_search_duration_seconds", "Vector search latency", ["collection"])
GRAPH_QUERY_DURATION = Histogram("graph_query_duration_seconds", "Graph query latency", ["operation"])


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = settings.csp_policy
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request.state.request_id if hasattr(request.state, "request_id") else ""
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up", database_url=settings.database_url[:30] + "...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    try:
        from app.ingestion.chroma.vector_store import initialize_vector_store

        await initialize_vector_store()
        logger.info("vector_store_initialized")
    except Exception as e:
        logger.warning("vector_store_init_skipped", error=str(e))

    try:
        from app.graph.neo4j import initialize_knowledge_graph

        await initialize_knowledge_graph()
        logger.info("knowledge_graph_initialized")
    except Exception as e:
        logger.warning("knowledge_graph_init_skipped", error=str(e))

    try:
        await event_bus.start()
        logger.info("event_bus_started")
    except Exception as e:
        logger.warning("event_bus_start_failed", error=str(e))

    try:
        from app.core.cache import wire_cache_invalidation

        wire_cache_invalidation()
        logger.info("cache_invalidation_wired")
    except Exception as e:
        logger.warning("cache_invalidation_wiring_failed", error=str(e))

    _periodic_task = None
    try:
        from app.ingestion.legal_data_ingestor import ingestor

        _periodic_task = asyncio.create_task(ingestor.start_periodic_updates(3600))
        logger.info("legal_data_updater_started")
    except Exception as e:
        logger.warning("legal_data_updater_start_failed", error=str(e))

    yield

    shutdown_timeout = 10.0
    logger.info("shutting_down", timeout=shutdown_timeout)

    try:
        from app.ingestion.legal_data_ingestor import ingestor

        ingestor.stop()
    except Exception:
        pass
    if _periodic_task:
        _periodic_task.cancel()
        try:
            await asyncio.wait_for(_periodic_task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    await event_bus.stop()
    logger.info("event_bus_stopped")

    await close_driver()
    await close_http_clients()
    await engine.dispose()
    try:
        from app.middleware.rate_limit import rate_limit_manager

        await rate_limit_manager.close()
    except Exception:
        pass
    logger.info("shutdown_complete")


app = FastAPI(
    title="BNS AI",
    description="Indian Legal AI Platform - Offline First",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

if OTEL_AVAILABLE and os.getenv("OTEL_ENABLED", "").lower() in ("1", "true", "yes"):
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    try:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except Exception as e:
        logger.warning("otlp_exporter_init_failed", error=str(e))

    prometheus_reader = PrometheusMetricReader()
    meter_provider = SdkMeterProvider(metric_readers=[prometheus_reader])

    FastAPIInstrumentor.instrument_app(app)
    if hasattr(engine, "sync_engine"):
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    else:
        SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    tracer = trace.get_tracer(__name__)
    meter = meter_provider.get_meter(__name__)
else:
    tracer = None
    meter = None
    if OTEL_AVAILABLE:
        logger.info("opentelemetry_disabled_set_OTEL_ENABLED=true")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    import time

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    endpoint = request.url.path
    method = request.method
    status_code = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    return response


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CSPMiddleware)
app.add_middleware(RequestLimitsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=3600,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": request.url.path},
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(drafting.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(user_settings.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_prompts.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")
app.include_router(retrieval.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "BNS AI API", "version": "1.0.0", "docs": "/docs"}
