# BNS AI — Backend Implementation Plan

> **Version:** 1.0
> **Companion docs:** `BACKEND_GAP_ANALYSIS.md`, `docs/architecture.md`,
> `BNS_AI_Master_Build_Specification.md`
>
> **Rule:** Implement → Test → Verify → Fix → Continue. Never build on a failing
> foundation. Phase N+1 starts only when Phase N is stable.

---

## 1. Guiding Invariants

1. **Retrieval is the source of legal truth.** The LLM never supplies BNS law.
2. **Fail closed.** No evidence ⇒ `INSUFFICIENT_BNS_EVIDENCE`, never model-memory guess.
3. **Separate trust domains.** User input, uploaded docs, retrieved chunks, prompts,
   model output are distinct; user/retrieved content is never instructions.
4. **Controlled agents.** Typed tool contracts, max steps, timeouts, audit.
5. **Source governance.** Sources are versioned; only `ACTIVE` versions enter RAG.
6. **Migrations only.** No `create_all()` for production schema.
7. **One chat engine, two modalities.** Voice and text share the Legal Chat pipeline.
8. **Do not modify the frontend.** Keep the existing API contract intact.

---

## 2. Module Boundaries (target layout under `backend/app/`)

```text
app/
├── main.py                  # FastAPI factory + lifespan + router mount
├── api/v1/                  # versioned routers (thin, orchestration only)
├── core/                    # config, security, exceptions, logging, middleware, request_id
├── db/                      # base, session, repositories/
├── models/                  # SQLAlchemy models (grouped by domain)
├── schemas/                 # Pydantic v2 schemas
├── auth/                    # jwt, password, sessions, rbac, dependencies
├── ai/
│   ├── orchestration/       # orchestrator, workflow_router, intent
│   ├── agents/              # typed agents with tool contracts
│   ├── llm/                 # base, router, ollama, gemini
│   ├── prompts/             # registry, builder, workflows/
│   ├── validation/          # grounding, citation, domain, injection, sections
│   ├── memory/              # short-term, summary, entity, case
│   └── evaluation/          # metrics, golden dataset runner
├── rag/
│   ├── ingestion/           # pipeline, extractors, ocr, legal_chunker, indexer
│   ├── embeddings/          # embedding provider abstraction
│   ├── retrieval/           # planner, exact, lexical, semantic, graph, hybrid, reranker
│   ├── context/             # context_builder (token budget)
│   └── citations/           # citation engine
├── legal/
│   ├── chat/                # chat service, conversation, memory glue
│   ├── drafting/            # templates, questionnaire, validators, versioning, export
│   ├── research/
│   ├── document_analysis/
│   └── case_intelligence/   # cases, facts, evidence, contradictions, elements
├── voice/                   # stt/tts abstractions + transcript validator
├── jobs/                    # background job abstraction (queued states)
├── storage/                 # file storage abstraction
├── audit/                   # audit_events writer
└── telemetry/               # metrics (Prometheus) + tracing hooks
```

---

## 3. Phases

### Phase 0 — Repository Audit ✅ (done)
Produced `BACKEND_GAP_ANALYSIS.md`.

### Phase 1 — Core Backend Foundation
- Project scaffold per module boundaries.
- Centralized config (`core/config.py`, `pydantic-settings`) with env separation.
- Structured JSON logging (`core/logging.py`, structlog).
- Exception hierarchy + global handlers + structured error contract + request IDs.
- Async SQLAlchemy engine/session (`db/`), Alembic setup + initial migration.
- `main.py` factory with lifespan; request-ID + logging + CORS + security headers middleware.
- `GET /api/v1/health`, `/health/live`, `/health/ready` (real dependency checks).
- `Dockerfile`, `requirements.txt`/`pyproject` dependencies, CI wiring, `.env.example`.
- Phase-1 tests (health, config, error contract, middleware, DB session) + lint + mypy.

**Exit criteria:** app imports, health endpoints return live/ready with real checks,
migrations apply, tests pass, ruff/mypy clean, docker image builds.

### Phase 2 — Identity + RBAC
- `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `auth_sessions`.
- register/login/refresh/logout/me; refresh rotation; bcrypt; JWT access tokens.
- Permission dependency factory; object-level authorization helpers.
- Tests: auth flow, refresh rotation, RBAC, permission denial.

### Phase 3 — Source Management
- `legal_sources`, `source_versions`, `ingestion_jobs`.
- Admin upload, checksum, duplicate detection, state machine
  (UPLOADED → PENDING_PROCESSING → PROCESSING → PROCESSED → PENDING_REVIEW →
  APPROVED → ACTIVE | FAILED | REJECTED | INACTIVE | ARCHIVED).
- Only `ACTIVE` versions are authoritative for RAG.

### Phase 4 — Ingestion Pipeline
- Text extraction (PDF/DOCX/TXT), OCR abstraction, cleaning, normalization.
- Structure detection: Act → Chapter → Section → Subsection → Explanation /
  Proviso / Exception / Illustration.
- **Legal-aware chunker** with full metadata + `parent_chunk_id` + `content_hash`.
- Embedding generation via configurable provider; vector/lexical indexing.
- Ingestion quality gates; source not activated until complete.

### Phase 5 — Embeddings + Vector Storage
- `EmbeddingProvider` abstraction; dimension read from model, never hardcoded.
- `VectorStore` abstraction (add/update/delete/search/health/stats) over Chroma.

### Phase 6 — Retrieval
- Exact (section) lookup, lexical (PostgreSQL FTS), semantic, graph.
- Retrieval planner + hybrid merge + dedup + reranker (configurable weights).

### Phase 7 — Knowledge Graph (Neo4j)
- Governed schema: Act/Chapter/Section/Concept/Offence/Definition/Punishment/
  Exception/Source; relationships CONTAINS/REFERENCES/RELATED_TO/DEFINES/
  HAS_PUNISHMENT/HAS_EXCEPTION/SUPERSEDES.
- Source-grounded ingestion into graph; graph retrieval service.

### Phase 8 — Reranking + Context Builder
- Weighted reranker; token-budget-aware context builder preserving citation IDs
  and statutory hierarchy.

### Phase 9 — Query + Security Validation
- Query validator, input sanitizer, prompt-injection validator, BNS domain
  validator, intent classifier, coreference/memory resolution glue.
- `AMBIGUOUS_QUERY`, `OUT_OF_BNS_SCOPE`, `PROMPT_INJECTION_DETECTED` handling.

### Phase 10 — Prompt System + LLM Router
- Versioned prompt registry; system/workflow/task builders.
- `LLMProvider` (Ollama, Gemini); router with availability, privacy policy
  (LOCAL_ONLY/CLOUD_ALLOWED/CLOUD_REDACTED), retries, timeouts, telemetry.

### Phase 11 — Agentic Orchestration
- Orchestrator + workflow router + agents (query, retrieval, evidence, analysis,
  drafting, research, case, citation, validation) with typed contracts, max steps,
  timeouts, retry policies, audit.

### Phase 12 — Response + Citation Validation
- Structured output parsing, claim extraction, evidence mapping, grounding check,
  citation engine + citation validator, retry/remove/reject logic.

### Phase 13 — Conversation Memory
- Short-term, summary, entity memory, case memory; coreference resolution with
  confidence; memory invalidation on topic change.

### Phase 14 — Legal Chat
- Full chat pipeline wiring; conversations/messages/message_citations tables;
  response builder; persistence + audit; streaming-ready validation boundary.

### Phase 15 — Legal Drafting
- Template engine, dynamic questionnaire, conditional fields, fact confirmation,
  scope validation, drafting agent, fact/legal/section/quality validators,
  versioning, export (DOCX/PDF/HTML/MD).

### Phase 16 — Legal Research
- Research planner, bounded subqueries, evidence pool, synthesis, reports,
  sessions + runs tables.

### Phase 17 — Document Analysis
- Secure upload, extraction, segmentation, issue detection, BNS retrieval,
  analysis, grounding, report; strict user-doc vs legal-source separation.

### Phase 18 — Case Intelligence
- Cases, members, parties, facts (provenance), evidence, timeline, contradictions,
  missing-facts, candidate provisions, element-of-offence mapping, alternative
  scenarios, outcome-scenario analysis, case follow-up, versioning, RBAC, audit.

### Phase 19 — Voice Legal Chat
- STT/TTS provider abstractions; transcript validation with legal-entity
  confidence; shared conversation_id; chat state preserved on voice failure.

### Phase 20 — Evaluation Framework
- Retrieval metrics (P@K, R@K, MRR, nDCG), generation metrics (groundedness,
  citation correctness/completeness, unsupported-claim rate), operational metrics.
- Golden BNS dataset runner (categories: exact section, definition, punishment,
  scenario, comparison, typo, ambiguous, pronoun, out-of-scope, injection, fake
  section, insufficient evidence, case, drafting).
- Adversarial hallucination + memory + voice + case tests.

### Phase 21 — Security + Observability Hardening
- Rate-limit tiers, audit everywhere, secrets management, secure headers,
  retention, Prometheus metrics, dashboards.

### Phase 22 — Docker + CI/CD Verification
- Dev + prod compose against new backend; health checks; CI (ruff, mypy, pytest,
  migration check, docker build) green.

---

## 4. API Surface (versioned `/api/v1`)

| Group | Routes |
| ----- | ------ |
| auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me` |
| users | `/users/me` |
| chat | `/chat/`, `/chat/{id}`, `/chat/{id}/stream` |
| drafting | `/drafting/types`, `/drafting/templates/{type}`, `/drafting/questionnaire/{type}`, `/drafting/questionnaire/{type}/validate`, `/drafting/questionnaire/{type}/suggest`, `/drafting/generate`, `/drafting/save`, `/drafting/documents`, `/drafting/documents/{id}` |
| documents | `/documents/`, `/documents/{id}`, `/documents/admin/all` |
| ingestion | `/ingestion/ingest/{fileId}`, `/ingestion/jobs`, `/ingestion/jobs/{id}`, `/ingestion/admin/jobs` |
| research | `/research/sessions`, `/research/runs`, `/research/reports/{id}` |
| cases | `/cases`, `/cases/{id}/facts`, `/cases/{id}/evidence`, `/cases/{id}/analysis`, `/cases/{id}/timeline`, `/cases/{id}/contradictions` |
| voice | `/voice/transcribe`, `/voice/synthesize` |
| sources | `/admin/sources`, `/admin/sources/{id}/versions`, `/admin/sources/{id}/activate` |
| feedback | `/feedback` |
| health | `/health/live`, `/health/ready`, `/api/v1/health` |
| dashboard | `/dashboard/` |
| admin | `/admin/*` |

Frontend-compatible routes (`/api/v1/...`) preserved verbatim.

---

## 5. Error Contract

```json
{
  "error": {
    "code": "INSUFFICIENT_BNS_EVIDENCE",
    "message": "The available BNS sources do not provide sufficient evidence to answer this question reliably.",
    "request_id": "req_..."
  }
}
```

Codes: `INVALID_REQUEST`, `AUTHENTICATION_REQUIRED`, `INVALID_CREDENTIALS`,
`TOKEN_EXPIRED`, `PERMISSION_DENIED`, `OUT_OF_BNS_SCOPE`, `AMBIGUOUS_QUERY`,
`INSUFFICIENT_INFORMATION`, `PROMPT_INJECTION_DETECTED`, `RETRIEVAL_FAILED`,
`INSUFFICIENT_BNS_EVIDENCE`, `LLM_PROVIDER_UNAVAILABLE`, `LLM_GENERATION_FAILED`,
`GROUNDING_VALIDATION_FAILED`, `CITATION_VALIDATION_FAILED`, `DRAFT_INCOMPLETE`,
`DRAFT_VALIDATION_FAILED`, `DOCUMENT_PROCESSING_FAILED`,
`VOICE_TRANSCRIPTION_FAILED`, `VOICE_TRANSCRIPTION_UNCERTAIN`,
`CASE_ACCESS_DENIED`, `SOURCE_NOT_ACTIVE`, `INGESTION_FAILED`, `INTERNAL_ERROR`.

---

## 6. Definition of Done (per phase)

- Implementation complete and typed; no TODOs/placeholders/fakes.
- Alembic migration exists where schema changes.
- Authorization applied; structured errors; audit where required.
- Tests pass; ruff + mypy clean; docker builds.
- Frontend contract preserved; `docs/` updated; phase exit criteria met.
