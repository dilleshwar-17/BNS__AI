from app.logging import get_logger

logger = get_logger(__name__)


class EmailIntegration:
    async def send(self, to: str, subject: str, body: str):
        logger.info("email_send_requested", to=to, subject=subject)
