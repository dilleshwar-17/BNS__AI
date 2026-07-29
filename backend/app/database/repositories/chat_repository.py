from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.chat import Chat
from app.database.models.message import Message


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_chats(self, user_id: str) -> list[Chat]:
        result = await self.db.execute(select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc()))
        return result.scalars().all()

    async def get_by_id(self, chat_id: str, user_id: str) -> Chat | None:
        result = await self.db.execute(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_messages(self, chat_id: str) -> list[Message]:
        result = await self.db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at))
        return result.scalars().all()

    async def create(self, chat: Chat) -> Chat:
        self.db.add(chat)
        await self.db.flush()
        return chat

    async def delete(self, chat: Chat):
        await self.db.delete(chat)
        await self.db.flush()
