from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.audit import Audit


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(self, audit: Audit) -> Audit:
        self.db.add(audit)
        await self.db.flush()
        return audit

    async def get_user_logs(self, user_id: str, limit: int = 50) -> list[Audit]:
        result = await self.db.execute(
            select(Audit).where(Audit.user_id == user_id).order_by(Audit.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
