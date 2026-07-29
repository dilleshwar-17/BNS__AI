from app.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    async def send_email(self, to: str, subject: str, body: str):
        logger.info("email_sent", to=to, subject=subject)
