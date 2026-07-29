import hashlib
import json
import time
from collections import OrderedDict

from app.core.logging import get_logger

logger = get_logger(__name__)

LLM_CACHE_MAX = 500
VECTOR_CACHE_MAX = 1000
SESSION_CACHE_MAX = 200


def make_cache_key(*args, **kwargs) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class MemoryCache:
    def __init__(self, ttl: int = 300, max_size: int = 500):
        self._cache: OrderedDict[str, tuple[object, float]] = OrderedDict()
        self._ttl = ttl
        self._max_size = max_size

    def get(self, key: str):
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                self._cache.move_to_end(key)
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: object, ttl: int | None = None):
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (value, time.time() + (ttl or self._ttl))

    def clear(self):
        self._cache.clear()

    def invalidate(self, key: str):
        self._cache.pop(key, None)

    def get_stats(self) -> dict:
        now = time.time()
        total = len(self._cache)
        expired = sum(1 for _, (_, exp) in self._cache.items() if now >= exp)
        return {"total_keys": total, "expired_pending": expired, "max_size": self._max_size}


llm_cache = MemoryCache(ttl=300, max_size=LLM_CACHE_MAX)
vector_cache = MemoryCache(ttl=600, max_size=VECTOR_CACHE_MAX)
session_cache = MemoryCache(ttl=120, max_size=SESSION_CACHE_MAX)


def get_cache() -> MemoryCache:
    return llm_cache


class CacheInvalidator:
    def __init__(self):
        self._patterns: dict[str, list] = {}

    def register(self, event_type: str, cache_keys_fn):
        if event_type not in self._patterns:
            self._patterns[event_type] = []
        self._patterns[event_type].append(cache_keys_fn)

    async def invalidate(self, event_type: str, payload: dict):
        fns = self._patterns.get(event_type, [])
        for fn in fns:
            try:
                keys = fn(payload) if callable(fn) else []
                for key in keys:
                    llm_cache.invalidate(key)
                    vector_cache.invalidate(key)
                    session_cache.invalidate(key)
                    logger.debug("cache_invalidated", event_type=event_type, key=key)
            except Exception as e:
                logger.error("cache_invalidation_error", event_type=event_type, error=str(e))


cache_invalidator = CacheInvalidator()


def _invalidate_on_chat(payload: dict) -> list[str]:
    user_id = payload.get("user_id", "")
    return [f"chat:*:{user_id}:*", f"session:*:{user_id}"]


def _invalidate_on_document(payload: dict) -> list[str]:
    doc_id = payload.get("document_id", "")
    return [f"doc:*:{doc_id}:*", f"vector:*:{doc_id}"]


def _invalidate_on_ingestion(payload: dict) -> list[str]:
    return ["vector:*", "llm_cache:*"]


cache_invalidator.register("chat.created", _invalidate_on_chat)
cache_invalidator.register("chat.message_sent", _invalidate_on_chat)
cache_invalidator.register("document.created", _invalidate_on_document)
cache_invalidator.register("document.updated", _invalidate_on_document)
cache_invalidator.register("document.deleted", _invalidate_on_document)
cache_invalidator.register("ingestion.completed", _invalidate_on_ingestion)


def wire_cache_invalidation():
    try:
        from app.core.events import subscribe_to

        @subscribe_to("chat.created")
        async def on_chat_created(event):
            await cache_invalidator.invalidate("chat.created", event.payload)

        @subscribe_to("chat.message_sent")
        async def on_chat_message(event):
            await cache_invalidator.invalidate("chat.message_sent", event.payload)

        @subscribe_to("document.created")
        async def on_doc_created(event):
            await cache_invalidator.invalidate("document.created", event.payload)

        @subscribe_to("document.updated")
        async def on_doc_updated(event):
            await cache_invalidator.invalidate("document.updated", event.payload)

        @subscribe_to("document.deleted")
        async def on_doc_deleted(event):
            await cache_invalidator.invalidate("document.deleted", event.payload)

        @subscribe_to("ingestion.completed")
        async def on_ingestion(event):
            await cache_invalidator.invalidate("ingestion.completed", event.payload)

        logger.info("cache_invalidation_wired")
    except Exception as e:
        logger.warning("cache_invalidation_wiring_failed", error=str(e))
