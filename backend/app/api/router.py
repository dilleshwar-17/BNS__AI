from fastapi import APIRouter

from app.api.v1 import admin_prompts, auth, chat, drafting, health

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1")
api_router.include_router(chat.router, prefix="/v1")
api_router.include_router(drafting.router, prefix="/v1")
api_router.include_router(health.router, prefix="/v1")
api_router.include_router(admin_prompts.router, prefix="/v1")
