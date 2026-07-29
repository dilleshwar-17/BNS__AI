from app.logging import get_logger

logger = get_logger(__name__)


class RedisIntegration:
    def __init__(self):
        self._client = None

    async def get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as aioredis

                from app.core.settings import get_settings

                self._client = aioredis.from_url(get_settings().redis_url, socket_connect_timeout=3)
            except Exception as e:
                logger.warning("redis_connect_failed", error=str(e))
        return self._client

    async def ping(self) -> bool:
        try:
            client = await self.get_client()
            if client:
                await client.ping()
                return True
        except Exception:
            pass
        return False

    async def get(self, key: str) -> str | None:
        try:
            client = await self.get_client()
            if client:
                data = await client.get(key)
                return data.decode() if data else None
        except Exception:
            pass
        return None

    async def set(self, key: str, value: str, ttl: int = 300):
        try:
            client = await self.get_client()
            if client:
                await client.setex(key, ttl, value)
        except Exception:
            pass
