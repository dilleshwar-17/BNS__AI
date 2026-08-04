# BNS AI — Backend Gap Analysis

> **Date:** 2026-08-01
> **Scope:** Backend-only. The frontend must not be modified.
> **Status:** Baseline established after deletion of `backend/` (recoverable in git at `HEAD`).

---

## 0. Executive Summary

The backend was **deleted** by decision (`backend/` now contains only `.env`).
The previous implementation remains fully recoverable in git (`git show HEAD:<path>`)
and was 317 files. It was a functional but **thin** RAG+FastAPI application with a
navy/blue frontend pairing. It does **not** satisfy the new specification's core
requirements:

- fail-closed legal grounding with **claim extraction + evidence mapping**,
- a real **agentic RAG orchestrator** with controlled agents and tool contracts,
- **case intelligence** (facts, provenance, contradictions, elements mapping, versioning),
- **voice** pipeline (STT/TTS abstraction + legal transcript validation),
- source lifecycle **ingestion → validation → activation** with versioning,
- **Neo4j**-grounded knowledge graph (the old graph module was shallow),
- **query validation / BNS domain validation / prompt-injection** pipeline.

Because the backend is empty, the gaps below are primarily **replacement**
(rewrite-to-spec) gaps rather than incremental patches. The gap analysis classifies
each item against the new master specification.

---

## 1. Current Backend Architecture (Baseline Recovered from Git)

### 1.1 High-level layout (old, in git)

```text
backend/
├── alembic/                 (2 migrations: initial + audit/document_versions)
├── app/
│   ├── main.py
│   ├── api/v1/              (auth, chat, drafting, documents, admin, health, ...)
│   ├── core/                (config, security, jwt, cache, exceptions, response)
│   ├── database/            (session, base, repositories, models)
│   ├── ai/                  (agents, orchestrator, llms, prompts, retrieval, validators)
│   ├── ingestion/           (pipeline, extractors, chunking, chroma)
│   ├── graph/               (neo4j client + search + builder)
│   ├── documents/           (pdf, docx, exporter)
│   ├── middleware/          (auth, cors, logging, rate_limit, request_id, injection)
│   ├── services/            (auth, chat, drafting, analytics, email, notification)
│   └── schemas/
├── scripts/                 (ingest_pdfs, ingest_acts, seed, backup, health_check)
└── requirements.txt
```

### 1.2 What the old backend actually did

| Capability | Old implementation | Notes |
| ---------- | ------------------ | ----- |
| Auth | JWT register/login/refresh, bcrypt | No refresh-token **rotation** DB table; tokens only |
| Chat | CRUD + LLM chat, mode selector | No entity memory / coreference resolution persisted |
| Drafting | 10 template JSONs, questionnaire, generate | One-shot generate; limited fact-fidelity validation |
| RAG | Chroma + BGE embeddings, hybrid lexical/semantic, reranker | No source lifecycle/versioning; ad-hoc ingestion |
| LLM | Ollama + Gemini behind router | No privacy-aware routing (LOCAL_ONLY / CLOUD_ALLOWED) |
| Validation | Prompt + output + hallucination + citation validators | No claim-level grounding pipeline with evidence IDs |
| Graph | Neo4j client + simple search | No governed schema; relationships not source-grounded |
| Observability | structured logging | No run tables (retrieval_runs, llm_runs, agent_runs) |

### 1.3 Environment / deployment facts (present and authoritative)

| Item | Value | Source |
| ---- | ----- | ------ |
| Docker Compose | postgres16, redis7, neo4j5, chroma0.5, ollama, api, frontend | `docker-compose.yml` |
| API port | `8000` (host `${API_PORT:-8000}`) | docker-compose |
| Frontend API base | `http://localhost:8003/api/v1` (dev) | `frontend/js/api.js` |
| DB URL scheme | `postgresql+asyncpg://` | `.env.example` |
| Frontend contract | `/auth/*`, `/chat/*`, `/drafting/*`, `/documents/*`, `/dashboard/`, `/ingestion/*`, `/users/me` | `frontend/js/**` |
| CI | backend.yml runs pytest + ruff | `.github/workflows/backend.yml` |
| Prometheus | scrapes `api:8000/metrics` | `infrastructure/monitoring/prometheus.yml` |

---

## 2. Existing APIs (Baseline)

`docs/api.md` + frontend contract give the required surface:

| Method | Path (under `/api/v1`) | Used by frontend |
| ------ | ---------------------- | ---------------- |
| POST | `/auth/register`, `/auth/login`, `/auth/refresh` | yes |
| GET  | `/auth/me`, `/users/me` | yes |
| GET/POST | `/chat/` | yes |
| GET/POST/DELETE | `/chat/{id}` | yes |
| POST | `/chat/{id}/stream` | spec (streaming) |
| GET | `/drafting/types`, `/drafting/templates/{type}`, `/drafting/questionnaire/{type}` | yes |
| POST | `/drafting/questionnaire/{type}/validate`, `/suggest`, `/drafting/generate`, `/drafting/save` | yes |
| GET/DELETE | `/drafting/documents`, `/drafting/documents/{id}` | yes |
| GET/DELETE | `/documents/{id}`, `/documents/admin/all` | yes |
| POST | `/ingestion/ingest/{fileId}`, `/ingestion/jobs` | yes |
| GET | `/ingestion/jobs/{jobId}`, `/ingestion/admin/jobs` | yes |
| GET | `/dashboard/` | yes |
| GET | `/api/v1/health` | yes |

**Gap:** The spec requires `/api/v1/voice`, `/api/v1/research`, `/api/v1/cases`,
`/api/v1/admin`, `/api/v1/feedback`, plus `/health/live` and `/health/ready`,
versioned prompts, sources lifecycle, and structured error codes. These are new.

---

## 3. Existing Database Schema (Baseline)

Tables previously created: users, chats, messages, documents, drafts, audits,
feedback, analytics, prompts, templates, roles/permissions, ingestion_jobs,
uploaded_files, embeddings, settings.

**Gap vs spec:** Missing `legal_sources`, `source_versions`, `legal_chunks`,
`citations`, `claim_evidence`, `conversation_memories`, `conversation_entities`,
`cases` + case_* family, `research_sessions`/`research_runs`, `draft_versions`,
`prompt_versions`, `retrieval_runs`, `llm_runs`, `agent_runs`, `validation_runs`,
`voice_transcripts`, `auth_sessions` (refresh rotation). Alembic only had 2
revisions; the spec mandates proper migration discipline.

---

## 4. Existing RAG / Ingestion / Retrieval (Baseline)

- ChromaDB vector store (`chromadb/chroma:0.5.0`), BGE-family embeddings.
- Hybrid search (lexical + semantic), reranker, context builder existed but were
  wired directly and not governed by a source lifecycle.
- Neo4j used for simple graph search.
- No legal-aware chunking preserving Act → Chapter → Section → Subsection →
  Explanation / Proviso / Exception / Illustration.
- No chunk metadata model (chapter/section/subsection/authority/checksum/hash).

---

## 5. Existing LLM / Prompts / Validation (Baseline)

- Ollama + Gemini providers behind a router with retry and health.
- 3-layer prompts (system/workflow/task) existed; prompts were files, not a
  **versioned registry** in DB.
- Validators existed (query, prompt, citation, hallucination, output) but not as a
  single composable validation pipeline with structured claim extraction.

---

## 6. Existing Tests (Baseline)

- pytest suite in `backend/app/tests/` (api, drafting, ingestion, ai pipeline,
  rate limit, imports).
- No golden BNS evaluation dataset with expected source IDs.
- No adversarial hallucination tests, no memory/coreference tests, no voice tests,
  no case intelligence tests, no citation-membership tests.

---

## 7. Existing Docker / CI (Baseline)

- `docker-compose.yml` (dev) and `docker-compose.prod.yml` both target
  `backend/Dockerfile` with services postgres/redis/neo4j/chroma/ollama/api/frontend.
- `backend.yml` CI: pytest + ruff; expects `backend/requirements.txt`.
- Prometheus scrapes `/metrics`.

---

## 8. Security Findings (Baseline + spec review)

| # | Severity | Finding |
| - | -------- | ------- |
| S1 | CRITICAL | Secrets in `.env` are git-ignored but `.env.example` seeds weak defaults (e.g. `bnsai_secret_key_change_in_production` in compose). Must require strong `SECRET_KEY`. |
| S2 | CRITICAL | Old refresh tokens were not revocable/rotated in DB. Spec requires `auth_sessions` + rotation. |
| S3 | HIGH | No object-level authorization (case membership) — only role checks. |
| S4 | HIGH | Prompt-injection middleware existed but no trust-boundary separation for retrieved documents / uploaded docs as *data*. |
| S5 | HIGH | No BNS domain validation — an out-of-scope legal question could be answered from model memory. |
| S6 | HIGH | Knowledge-fallback and provider-fallback conflated; spec forbids "RAG empty → ask Gemini". |
| S7 | MEDIUM | No rate-limit tiers per endpoint cost (chat vs ingestion vs research). |
| S8 | MEDIUM | File upload validation (MIME/size/signature) needs hardening. |
| S9 | MEDIUM | No privacy-aware LLM routing (LOCAL_ONLY / CLOUD_ALLOWED / CLOUD_REDACTED). |
| S10 | LOW | CORS list ok, CSP defined; must remain in new app. |

---

## 9. Missing Components (vs Master Specification)

| Priority | Component |
| -------- | --------- |
| CRITICAL | Claim extraction + evidence mapping + grounding validation (fail-closed) |
| CRITICAL | Source lifecycle + versioning (ingestion → approval → active) |
| CRITICAL | Legal-aware chunking with full metadata |
| CRITICAL | Query / BNS-domain / prompt-injection validation pipeline |
| HIGH | Agentic orchestrator with typed agents + tool contracts + audit |
| HIGH | Case Intelligence module (facts, provenance, contradictions, elements, versioning, RBAC) |
| HIGH | Conversation memory + coreference resolution |
| HIGH | Citation engine (metadata-driven) + citation validation |
| HIGH | LLM router with privacy-aware policies |
| HIGH | `/health/live` + `/health/ready` with real checks |
| HIGH | Structured error contract + request IDs end-to-end |
| HIGH | Golden BNS evaluation dataset + metrics |
| MEDIUM | Voice pipeline (STT/TTS abstractions + legal transcript validation) |
| MEDIUM | Research sessions, document analysis module |
| MEDIUM | Background jobs abstraction (ingestion/OCR/embeddings/research) |
| MEDIUM | Run tables (retrieval_runs, llm_runs, agent_runs, validation_runs) |
| LOW | Prompt registry with versioning |
| LOW | Feedback system wired to run metadata |

---

## 10. Technical Debt / Risks

1. **Empty backend**: must rebuild from scratch; do not re-import old monolithic
   `services/*` that scatter DB access.
2. **Frontend contract**: new API must keep `/api/v1/auth`, `/chat/*`,
   `/drafting/*`, `/documents/*`, `/dashboard/`, `/ingestion/*`, `/users/me`
   endpoints and their request/response shapes or the UI breaks. The frontend
   uses `{username, password}`, `{title, mode}`, `{message, mode}`,
   `{draft_type, details}`, and expects `data`/error objects.
3. **Python version skew**: local env is Python 3.11.9; spec + CI + Docker target
   **3.12**. `pyproject.toml` says `>=3.12` while ruff/mypy config targets 3.11.
4. **neo4j/chroma defaults**: compose seeds default credentials; production compose
   requires them (`:?`). Ensure config allows this split.
5. **Embedding dimension**: never hardcode; read from configured model.
6. **Chroma telemetry** disabled in compose; keep disabled.

---

## 11. Architectural Conflicts with the Specification

| Conflict | Old design | Spec requirement |
| -------- | ---------- | ---------------- |
| Source of truth | LLM fallback to memory possible | Fail-closed; insufficient evidence is a valid answer |
| Agent autonomy | Agents loosely orchestrated | Bounded agents: tools, schemas, max steps, audit |
| Schema evolution | `Base.metadata.create_all()` fallback | Alembic-only migrations |
| Memory | Per-chat only | Multi-layer (recent, summary, entity, case) + coreference |
| Retrieval | semantic-first | Hybrid exact+lexical+semantic+graph, planner-driven |
| Graph | ad-hoc | Source-grounded schema, no LLM-invented relationships |

---

## 12. Gap Classification Summary

| Severity | Count | Examples |
| -------- | ----- | -------- |
| CRITICAL | 8 | grounding, source lifecycle, legal chunking, query/domain/injection validation, object-level auth, no-create_all, provider/knowledge fallback split, run tables |
| HIGH | 12 | agentic orchestrator, case intelligence, memory+coreference, citations, privacy-aware routing, health ready, error contract, eval dataset, request-ids, voice, jobs, drafting versions |
| MEDIUM | 9 | document analysis, research, feedback, prompt registry, file storage abstraction, rate tiers, chunk quality, multilingual extension, streaming buffer |
| LOW | 6 | metrics, admin APIs polish, export formats, cache invalidation, retention, docs |

---

## 13. Recommendation

Rebuild `backend/` to the master specification using the phased plan in
`BACKEND_IMPLEMENTATION_PLAN.md`. Do **not** restore old code wholesale;
port only proven patterns (embedding client, document extraction, docker wiring)
into the new module boundaries. Preserve the frontend API contract.
