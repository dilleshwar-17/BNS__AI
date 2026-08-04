# Pre-Deployment Load Test — Run against a real Linux server

This documents how to stand up the backend for real, and run the 1000+ user
load test against it. The bundled GPU/hardware loop on the Windows dev box
cannot push the uvicorn HTTP layer past ~60 rps, so **the verification must
run on a Linux host with the production config** (gunicorn + uvloop).

## What was changed to make this possible

| Change | Why |
| ------ | --- |
| `backend/requirements.txt` | added `gunicorn` + `uvloop` |
| `backend/gunicorn.conf.py` | uvloop `UvicornWorker`s, auto workers from CPU count |
| `backend/Dockerfile` | runs `gunicorn -c gunicorn.conf.py app.main:app` |
| `docker-compose.prod.yml` | pool sizing env, worker override, `loadtest` profile |
| `backend/load_test.py` | async multi-worker harness; defaults 3000 users / 1000 concurrency |

## 1) Deploy on Linux (docker compose)

```bash
# on the Linux server
export POSTGRES_PASSWORD='...'
export NEO4J_PASSWORD='...'
export SECRET_KEY='...'        # openssl rand -hex 32
export CORS_ORIGINS='http://your.domain'
export POOL_SIZE=100           # pool raised from dev default for concurrency
export MAX_OVERFLOW=200

# build & start the stack
docker compose -f docker-compose.prod.yml up -d --build postgres redis neo4j chroma api

# optionally pull the ollama model used by the backend
docker compose -f docker-compose.prod.yml exec ollama ollama pull mistral

# verify readiness
docker compose -f docker-compose.prod.yml ps
curl -s http://localhost:8000/health/ready
```

## 2) — Run ingest first (retrieval needs data)

If this is a fresh database, ingest the BNS corpus so retrieval/search has
documents to scan:

```bash
docker compose -f docker-compose.prod.yml run --rm api \
    python run_pipeline.py
```

## 3) — Run the load test

From your local machine (or the server), execute the `loadtest` service:

```bash
export LOAD_USERS=3000
export LOAD_RISE=1000
export LOAD_DURATION=60

docker compose -f docker-compose.prod.yml run --rm --profile loadtest loadtest
```

The report is written to the service's container and mirrored to
`backend/LOAD_REPORT.md` via the volume mount.

Or run it directly against the exposed API:

```bash
cd backend
python load_test.py --host <SERVER_IP> --port 8000 --users 3000 --rise 1000 --duration 60
```

## 4) — What good looks like

Target SLO for the 200–500 ms goal:

- **p95 latency: ≤ 500 ms**
- **success rate: 100 %** (no transport timeouts, no 5xx)
- **throughput: ≥ 1000 RPS** at the rising concurrency
- **zero disconnects** during the 60 s window

`write_report` in `load_test.py` produces `LOAD_REPORT.md` with the full
endpoint breakdown (requests, errors, avg, p95 per route) and an outcome line.

## Tuning knobs

- **Workers**: `WEB_CONCURRENCY` (default auto = `max(2, min(16, cpus*2))`).
- **DB pool**: `POOL_SIZE` / `MAX_OVERFLOW` (defaults 50 / 100).
- **API replicas**: `API_REPLICAS` scales whole containers behind nginx.
- **Backlog / timeouts**: edit `gunicorn.conf.py` (`backlog`, `timeout`).
- **Load shape**: `LOAD_USERS`, `LOAD_RISE`, `LOAD_DURATION`.

> Note: `GUNICORN_ACCESSLOG` / `GUNICORN_LOGLEVEL` default to `-` / `info`.
> Under a very high RPS access-log writing can compete with work; set
> `GUNICORN_ACCESSLOG=/dev/null` to disable per-request logging during a
> throughput run.

> Gotcha: compose auto-reads a `.env` file in the CWD and it **overrides**
> `:-default` fallbacks. The repo root `.env` carries dev values (e.g.
> `POOL_SIZE=5`). On the prod server, either export the prod values (as above)
> or run with `--env-file` pointing at your own file — otherwise the dev pool
> size is silently used.
