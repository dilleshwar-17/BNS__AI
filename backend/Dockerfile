# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for chromadb and the app.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ .

# Create a non-root user.
RUN useradd --create-home --uid 1000 bnsai && chown -R bnsai:bnsai /app
USER bnsai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ready || exit 1

# Production: gunicorn manages uvloop Uvicorn workers. Worker count comes from
# WEB_CONCURRENCY or gunicorn.conf.py (auto-scaled to CPU count).
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
