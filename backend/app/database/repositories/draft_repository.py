from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.draft import Draft


class DraftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_drafts(self, user_id: str) -> list[Draft]:
        result = await self.db.execute(select(Draft).where(Draft.user_id == user_id).order_by(Draft.updated_at.desc()))
        return result.scalars().all()

    async def get_by_id(self, draft_id: str, user_id: str) -> Draft | None:
        result = await self.db.execute(select(Draft).where(Draft.id == draft_id, Draft.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, draft: Draft) -> Draft:
        self.db.add(draft)
        await self.db.flush()
        return draft

    async def delete(self, draft: Draft):
        await self.db.delete(draft)
        await self.db.flush()
