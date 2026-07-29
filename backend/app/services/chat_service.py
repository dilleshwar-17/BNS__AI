import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.chat import Chat
from app.database.models.message import Message


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chat(self, user_id: str, title: str = "New Chat", mode: str = "legal_guidance") -> Chat:
        chat = Chat(id=str(uuid.uuid4()), user_id=user_id, title=title, mode=mode)
        self.db.add(chat)
        await self.db.flush()
        return chat

    async def add_message(self, chat_id: str, role: str, content: str) -> Message:
        msg = Message(id=str(uuid.uuid4()), chat_id=chat_id, role=role, content=content)
        self.db.add(msg)
        await self.db.flush()
        return msg
