from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.chat import Chat
from app.database.models.document import Document
from app.database.models.message import Message
from app.database.models.uploaded_file import UploadedFile


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stats(self, user_id: str) -> dict:
        chat_count = await self.db.scalar(select(func.count(Chat.id)).where(Chat.user_id == user_id))
        doc_count = await self.db.scalar(select(func.count(Document.id)).where(Document.user_id == user_id))
        msg_count = await self.db.scalar(
            select(func.count(Message.id)).where(Message.chat_id == Chat.id, Chat.user_id == user_id)
        )
        file_count = await self.db.scalar(select(func.count(UploadedFile.id)).where(UploadedFile.user_id == user_id))
        return {
            "chats": chat_count or 0,
            "documents": doc_count or 0,
            "messages": msg_count or 0,
            "uploads": file_count or 0,
        }
