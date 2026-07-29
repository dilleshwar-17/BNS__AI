FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

RUN groupadd -r bnsai && useradd -r -g bnsai -d /app -s /sbin/nologin bnsai

WORKDIR /app

COPY --from=builder /root/.local /usr/local
COPY . .

RUN chown -R bnsai:bnsai /app

USER bnsai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/liveness')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
