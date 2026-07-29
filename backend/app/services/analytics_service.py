from app.database.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self.repo = repo

    async def track(
        self, user_id: str | None, event_type: str, event_data: dict | None = None, duration_ms: float | None = None
    ):
        import uuid

        from app.database.models.analytics import Analytics

        event = Analytics(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            event_data=str(event_data) if event_data else None,
            duration_ms=duration_ms,
        )
        await self.repo.record_event(event)
