from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_cors(app):
    from app.core.settings import get_settings

    settings = get_settings()
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        max_age=3600,
    )
    logger.info("cors_configured", origins=settings.cors_origins)
