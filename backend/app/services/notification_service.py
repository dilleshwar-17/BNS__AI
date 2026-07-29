import uuid

from app.database.models.analytics import Analytics
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, analytics_repo: AnalyticsRepository | None = None):
        self.repo = analytics_repo

    async def send(self, user_id: str, title: str, message: str, notification_type: str = "in_app"):
        logger.info("notification_sent", user_id=user_id, title=title, type=notification_type)
        if self.repo:
            event = Analytics(
                id=str(uuid.uuid4()),
                user_id=user_id,
                event_type=f"notification_{notification_type}",
                event_data=f"title={title}|message={message[:100]}",
            )
            await self.repo.record_event(event)
