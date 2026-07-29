import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.logging import get_logger

logger = get_logger(__name__)


class Message:
    def __init__(self, sender: str, msg_type: str, payload: dict, correlation_id: str | None = None):
        self.id = str(uuid.uuid4())
        self.sender = sender
        self.type = msg_type
        self.payload = payload
        self.correlation_id = correlation_id or self.id
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.reply_to: str | None = None

    def reply(self, payload: dict) -> "Message":
        return Message(
            sender=self.reply_to or "system",
            msg_type=f"{self.type}_response",
            payload=payload,
            correlation_id=self.correlation_id,
        )


class SpiderWeb:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.subscribers = defaultdict(list)
            cls._instance.history = []
            cls._instance.max_history = 10000
            cls._instance.pending = {}
            cls._instance.patterns = defaultdict(int)
        return cls._instance

    def subscribe(self, msg_type: str, callback: Callable, agent_name: str):
        self.subscribers[msg_type].append({"cb": callback, "agent": agent_name})
        logger.debug("spider_web_subscribed", agent=agent_name, msg_type=msg_type)

    def unsubscribe(self, msg_type: str, agent_name: str):
        self.subscribers[msg_type] = [s for s in self.subscribers[msg_type] if s["agent"] != agent_name]

    async def publish(self, message: Message) -> list[Any]:
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

        self.patterns[message.type] += 1

        results = []
        subscribers = list(self.subscribers.get(message.type, []))
        subscribers += list(self.subscribers.get("*", []))

        for sub in subscribers:
            try:
                if asyncio.iscoroutinefunction(sub["cb"]):
                    result = await sub["cb"](message)
                else:
                    result = sub["cb"](message)
                results.append({"agent": sub["agent"], "result": result})
            except Exception as e:
                logger.error("spider_web_error", agent=sub["agent"], msg_type=message.type, error=str(e))
                results.append({"agent": sub["agent"], "error": str(e)})

        return results

    async def request(self, message: Message, timeout: float = 30.0) -> Any:
        future = asyncio.get_event_loop().create_future()
        self.pending[message.correlation_id] = future

        async def response_handler(response_msg: Message):
            if response_msg.correlation_id == message.correlation_id:
                self.pending[message.correlation_id].set_result(response_msg)

        self.subscribe(f"{message.type}_response", response_handler, "_request_tmp")
        await self.publish(message)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            self.unsubscribe(f"{message.type}_response", "_request_tmp")
            return result
        except asyncio.TimeoutError:
            self.unsubscribe(f"{message.type}_response", "_request_tmp")
            return None

    def get_history(self, msg_type: str | None = None, limit: int = 50) -> list[Message]:
        if msg_type:
            filtered = [m for m in self.history if m.type == msg_type]
        else:
            filtered = self.history
        return filtered[-limit:]

    def get_stats(self) -> dict:
        return {
            "total_messages": len(self.history),
            "patterns": dict(self.patterns),
            "subscribers": {k: [s["agent"] for s in v] for k, v in self.subscribers.items()},
            "pending_requests": len(self.pending),
        }


web = SpiderWeb()
