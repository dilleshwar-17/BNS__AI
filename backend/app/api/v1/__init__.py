from app.api.v1.admin_prompts import router as admin_prompts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.drafting import router as drafting_router
from app.api.v1.health import router as health_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.upload import router as upload_router

__all__ = [
    "auth_router",
    "chat_router",
    "drafting_router",
    "health_router",
    "admin_prompts_router",
    "upload_router",
    "ingestion_router",
    "documents_router",
]
