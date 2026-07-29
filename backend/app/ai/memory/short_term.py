from collections import deque
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


class ShortTermMemory:
    def __init__(self, maxlen: int = 50):
        self.conversations: dict[str, deque] = {}
        self.maxlen = maxlen

    def add(self, session_id: str, role: str, content: str, metadata: dict | None = None):
        if session_id not in self.conversations:
            self.conversations[session_id] = deque(maxlen=self.maxlen)
        self.conversations[session_id].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }
        )

    def get(self, session_id: str, limit: int | None = None) -> list[dict]:
        if session_id not in self.conversations:
            return []
        items = list(self.conversations[session_id])
        if limit:
            items = items[-limit:]
        return items

    def get_recent(self, session_id: str, n: int = 5) -> list[dict]:
        return self.get(session_id, limit=n)

    def clear(self, session_id: str):
        self.conversations.pop(session_id, None)

    def get_all_sessions(self) -> list[str]:
        return list(self.conversations.keys())
