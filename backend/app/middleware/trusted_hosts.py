from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_trusted_hosts(app, allowed_hosts: list[str] | None = None):
    if not allowed_hosts:
        logger.warning("trusted_hosts_not_configured", message="All hosts allowed. Set TRUSTED_HOSTS for production.")
        allowed_hosts = ["*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    logger.info("trusted_hosts_configured", hosts=allowed_hosts)
