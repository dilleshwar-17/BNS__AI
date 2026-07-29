from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.document import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_documents(self, user_id: str) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, doc_id: str, user_id: str) -> Document | None:
        result = await self.db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, doc: Document) -> Document:
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def delete(self, doc: Document):
        await self.db.delete(doc)
        await self.db.flush()
