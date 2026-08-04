"""API v1 router aggregator.

Versioned endpoints only. Health/liveness/readiness routes are registered at
the root path in ``app.main`` (see ``/health/live``, ``/health/ready``).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    cases,
    chat,
    documents,
    drafting,
    ingestion,
    pleadings,
    reports,
    research,
    retrieval,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(documents.router, prefix="", tags=["documents"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(drafting.router, prefix="/drafting", tags=["drafting"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(pleadings.router, prefix="/pleadings", tags=["pleadings"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
