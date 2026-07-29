import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
DLQ_TTL_SECONDS = 86400  # 24 hours


class Event:
    def __init__(
        self,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        source: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.payload = payload
        self.correlation_id = correlation_id or self.id
        self.source = source
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.retry_count = 0
        self.max_retries = MAX_RETRIES

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "event_type": self.event_type,
                "payload": self.payload,
                "correlation_id": self.correlation_id,
                "source": self.source,
                "timestamp": self.timestamp,
                "retry_count": self.retry_count,
                "max_retries": self.max_retries,
            }
        )

    @classmethod
    def from_json(cls, data: str) -> "Event":
        d = json.loads(data)
        event = cls(d["event_type"], d["payload"], d.get("correlation_id"), d.get("source"))
        event.id = d["id"]
        event.timestamp = d["timestamp"]
        event.retry_count = d.get("retry_count", 0)
        event.max_retries = d.get("max_retries", MAX_RETRIES)
        return event


class EventBus:
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pubsub = None
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._dlq_name = "bnsai:events:dlq"

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def start(self):
        if self._running:
            return
        self._running = True
        r = await self._get_redis()
        self._pubsub = r.pubsub()
        await self._pubsub.subscribe("bnsai:events")
        self._consumer_task = asyncio.create_task(self._consume())
        logger.info("event_bus_started")

    async def stop(self):
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe("bnsai:events")
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("event_bus_stopped")

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)
        logger.debug("event_subscribed", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: Callable):
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: Event):
        r = await self._get_redis()
        await r.publish("bnsai:events", event.to_json())
        logger.debug("event_published", event_type=event.event_type, event_id=event.id)

    async def _send_to_dlq(self, event: Event, error: str):
        r = await self._get_redis()
        dlq_entry = {
            "event": event.to_json(),
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await r.rpush(self._dlq_name, json.dumps(dlq_entry))
            await r.expire(self._dlq_name, DLQ_TTL_SECONDS)
            logger.warning(
                "event_sent_to_dlq",
                event_type=event.event_type,
                event_id=event.id,
                error=error,
                retry_count=event.retry_count,
            )
        except Exception as e:
            logger.error("dlq_publish_failed", event_id=event.id, error=str(e))

    async def retry_event(self, event: Event):
        event.retry_count += 1
        if event.retry_count > event.max_retries:
            await self._send_to_dlq(event, "max_retries_exceeded")
            return
        delay = RETRY_BASE_DELAY * (2 ** (event.retry_count - 1))
        logger.info(
            "event_retry_scheduled",
            event_type=event.event_type,
            event_id=event.id,
            retry=event.retry_count,
            delay=delay,
        )
        asyncio.get_event_loop().call_later(delay, lambda: asyncio.ensure_future(self._retry_dispatch(event)))

    async def _retry_dispatch(self, event: Event):
        try:
            await self._dispatch(event)
        except Exception as e:
            await self._send_to_dlq(event, str(e))

    async def _consume(self):
        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue
                try:
                    event = Event.from_json(message["data"])
                    await self._dispatch(event)
                except Exception as e:
                    logger.error("event_consume_failed", error=str(e), message=message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("event_consumer_error", error=str(e))

    async def _dispatch(self, event: Event):
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    "handler_failed",
                    event_type=event.event_type,
                    handler=handler.__name__,
                    error=str(e),
                    retry_count=event.retry_count,
                )
                await self.retry_event(event)

    async def get_dlq_entries(self, limit: int = 50) -> list[dict]:
        r = await self._get_redis()
        entries = await r.lrange(self._dlq_name, 0, limit - 1)
        return [json.loads(e) for e in entries]

    async def replay_dlq_entry(self, index: int) -> bool:
        r = await self._get_redis()
        raw = await r.lindex(self._dlq_name, index)
        if not raw:
            return False
        entry = json.loads(raw)
        event = Event.from_json(entry["event"])
        event.retry_count = 0
        try:
            await self._dispatch(event)
            await r.lrem(self._dlq_name, 1, raw)
            return True
        except Exception:
            return False

    async def clear_dlq(self):
        r = await self._get_redis()
        await r.delete(self._dlq_name)


event_bus = EventBus()


async def publish_event(
    event_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None, source: Optional[str] = None
):
    event = Event(event_type, payload, correlation_id, source)
    await event_bus.publish(event)


def subscribe_to(event_type: str):
    def decorator(handler: Callable):
        event_bus.subscribe(event_type, handler)
        return handler

    return decorator
