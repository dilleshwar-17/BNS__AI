"""Production gunicorn configuration for the BNS AI backend.

Runs the FastAPI app with uvloop-backed Uvicorn workers so a single Linux host
can handle thousands of concurrent requests. Worker counts are derived from the
number of visible CPUs by default and can be overridden with WEB_CONCURRENCY.

Overrides for the exposed port / log levels are available via environment
variables (GUNICORN_BIND, WEB_CONCURRENCY, GUNICORN_LOGLEVEL, etc.).
"""

from __future__ import annotations

import multiprocessing
import os


def _cpu_count() -> int:
    try:
        return multiprocessing.cpu_count()
    except NotImplementedError:  # pragma: no cover - defensive
        return 2


def _workers() -> int:
    configured = os.getenv("WEB_CONCURRENCY")
    if configured and configured.isdigit():
        return int(configured)
    # Rule of thumb for an async app: 2-4 workers per core keep the event loops
    # busy without thrashing; 4 per core is generous for I/O-heavy workloads.
    return max(2, min(16, _cpu_count() * 2))


# --- Server ----------------------------------------------------------------
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048
timeout = 60

# --- Workers --------------------------------------------------------
# Use uvicorn's worker class so the ASGI app runs on uvloop.
worker_class = "uvicorn.workers.UvicornWorker"
workers = _workers()
threads = 1
max_requests = 2000
max_requests_jitter = 200
graceful_timeout = 30

# --- Logging --------------------------------------------------------
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
capture_output = True
