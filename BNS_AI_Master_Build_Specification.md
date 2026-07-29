# BNS AI Master Build Specification (Condensed)

> **Version:** 1.0
>
> **Purpose:** This document is the authoritative specification for
> building **BNS AI**, an offline-first, production-grade Indian Legal
> AI platform. It is intended to minimize ambiguity for LLM-assisted
> code generation.

------------------------------------------------------------------------

# 1. System Role

You are an expert software architect, backend engineer, frontend
engineer, DevOps engineer, database architect, UI/UX designer, and
security engineer.

Your objective is to generate a **complete, production-ready
repository**. Do **not** generate pseudocode, placeholders, TODOs, mock
implementations, or incomplete files.

------------------------------------------------------------------------

# 2. Primary Objectives

-   Offline-first legal assistant
-   Indian law focused (BNS, BNSS, BSA, Constitution, CPC, CrPC,
    Consumer Protection, IT Act)
-   Dockerized deployment
-   Modular architecture
-   Async backend
-   Vanilla JavaScript SPA
-   Graceful offline fallback
-   Secure authentication
-   Maintainable codebase

------------------------------------------------------------------------

# 3. Technology Stack

## Backend

-   Python 3.12
-   FastAPI
-   SQLAlchemy Async
-   PostgreSQL
-   Redis
-   Neo4j
-   ChromaDB
-   Ollama (Mistral)
-   Gemini Flash
-   Passlib
-   bcrypt \< 4.1
-   JWT

## Frontend

-   HTML5
-   CSS3
-   Vanilla JS
-   Markdown rendering

## Infrastructure

-   Docker Compose
-   Nginx

------------------------------------------------------------------------

# 4. Repository Layout

``` text
bnsai/
├── backend/
├── frontend/
├── nginx/
├── docker-compose.yml
```

Backend must include:

``` text
app/
    api/
    core/
    db/
    dependencies/
    middleware/
    models/
    schemas/
    services/
    utils/
```

------------------------------------------------------------------------

# 5. Engineering Rules

-   Fully typed Python.
-   PEP8 compliant.
-   Async where supported.
-   Clear separation of concerns.
-   Centralized configuration.
-   Structured logging.
-   Global exception handlers.
-   Dependency injection where appropriate.
-   No duplicated logic.

------------------------------------------------------------------------

# 6. Backend Requirements

Create:

-   FastAPI lifespan
-   CORS
-   Compression
-   Request logging
-   Request ID middleware
-   JWT auth
-   Audit middleware

Expose:

-   /docs
-   /redoc
-   /api/v1/\*

------------------------------------------------------------------------

# 7. Database

Models:

-   User
-   Chat
-   Message
-   Document
-   Audit

Relationships must be explicit.

Run `Base.metadata.create_all()` during lifespan.

------------------------------------------------------------------------

# 8. Authentication

JWT

Endpoints:

-   POST /register
-   POST /login
-   POST /refresh
-   POST /logout
-   GET /me

Requirements:

-   bcrypt hashing
-   refresh rotation
-   expiry
-   active-user validation

------------------------------------------------------------------------

# 9. Health Endpoint

Return service status for:

-   PostgreSQL
-   Redis
-   Neo4j
-   Chroma
-   Ollama
-   Gemini

Include statistics.

Never fail the endpoint because one dependency is unavailable.

------------------------------------------------------------------------

# 10. LLM Router

Priority:

1.  Ollama (Mistral)
2.  Gemini Flash
3.  Offline Knowledge Base

Features:

-   retries
-   timeout
-   circuit breaker
-   graceful fallback
-   structured logging

------------------------------------------------------------------------

# 11. Offline Legal Engine

Knowledge:

-   Theft
-   FIR
-   Bail
-   Divorce
-   Consumer Rights
-   Cyber Crime
-   Property
-   Constitution
-   Fundamental Rights
-   Civil Procedure
-   Criminal Procedure
-   Agreements

Support:

-   section lookup
-   drafting
-   legal guidance
-   procedure
-   citations

------------------------------------------------------------------------

# 12. Response Modes

Implement:

-   legal_guidance
-   legal_drafting
-   case_law
-   comparison
-   deep_research
-   document_analysis
-   legal_procedure
-   rights_advisory
-   section_lookup

------------------------------------------------------------------------

# 13. Draft Templates

Provide:

-   FIR
-   Legal Notice
-   Bail Application
-   Affidavit
-   Consumer Complaint
-   Agreement
-   Civil Plaint
-   Divorce Petition
-   Will

Every template must contain realistic headings, placeholders, signature
blocks, and Indian legal formatting.

------------------------------------------------------------------------

# 14. Frontend

Hash router:

-   /
-   /chat
-   /drafting
-   /dashboard
-   /login
-   /register

Theme:

-   Jade (#0d8a5e)
-   Gold (#b8860b)

Use:

-   Glassmorphism
-   Responsive layout
-   Dark/light mode
-   Animated gradients

------------------------------------------------------------------------

# 15. Chat

Features:

-   Markdown
-   History
-   Mode selector
-   Draft selector
-   Streaming-ready architecture
-   Copy
-   Export

------------------------------------------------------------------------

# 16. Drafting

Cards for all templates.

Buttons:

-   Generate
-   Copy
-   Download DOCX
-   New Draft

Keyboard shortcut:

Ctrl+Enter

------------------------------------------------------------------------

# 17. Docker

Services:

-   postgres
-   redis
-   neo4j
-   chroma
-   api
-   frontend

Health checks mandatory.

------------------------------------------------------------------------

# 18. Security

Implement:

-   JWT
-   Password hashing
-   Rate limiting
-   Validation
-   XSS protection
-   SQL injection protection
-   Audit logging

------------------------------------------------------------------------

# 19. Logging

Every request logs:

-   request id
-   endpoint
-   duration
-   user
-   status

Errors include stack traces.

------------------------------------------------------------------------

# 20. Acceptance Criteria

Repository must:

-   Build using `docker compose up --build`
-   Auto-create tables
-   Authenticate users
-   Persist chats
-   Persist documents
-   Perform vector search
-   Query Neo4j
-   Use Ollama first
-   Fall back to Gemini
-   Fall back to offline KB
-   Pass health checks
-   Serve frontend on :8080
-   Serve API on :8000

No TODOs. No placeholders. No fake implementations.

------------------------------------------------------------------------

# 21. LLM Generation Contract

Generate files **one at a time**.

For every file:

1.  Print filename.
2.  Print complete contents.
3.  Validate imports.
4.  Validate syntax.
5.  Continue automatically.

Never skip files.

Never abbreviate code.

------------------------------------------------------------------------

# 22. Self Validation Checklist

Before finishing:

-   All imports valid
-   No circular imports
-   Docker builds
-   API starts
-   Swagger works
-   Frontend loads
-   Auth works
-   Drafting works
-   Offline mode works
-   Health endpoint works
-   No placeholder text remains

------------------------------------------------------------------------

# End of Specification

This document acts as the canonical engineering specification for BNS
AI. Any generated implementation must conform to this specification
before it is considered complete.
