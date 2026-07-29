from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.analytics import Analytics


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(self, event: Analytics) -> Analytics:
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_event_count(self, event_type: str) -> int:
        result = await self.db.execute(select(func.count(Analytics.id)).where(Analytics.event_type == event_type))
        return result.scalar() or 0
