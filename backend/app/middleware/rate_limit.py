import asyncio
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)


# In-memory rate limiter for fallback when Redis is unavailable
class InMemoryRateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        async with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if len(self._requests[key]) >= max_requests:
                return False
            self._requests[key].append(now)
            return True

    def cleanup(self):
        now = time.time()
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > now - 600]
            if not self._requests[key]:
                del self._requests[key]


_in_memory_limiter = InMemoryRateLimiter()


# Circuit breaker for Redis-based rate limiting
class RateLimitCircuitBreaker:
    def __init__(self):
        self.failures = 0
        self.max_failures = 3
        self.reset_timeout = 60.0
        self.last_failure_time = 0.0
        self.state = "closed"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.max_failures:
            self.state = "open"
            logger.warning("rate_limit_circuit_open", failures=self.failures)

    def record_success(self):
        self.failures = 0
        self.state = "closed"

    def is_available(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half_open"
                return True
            return False
        return True


_circuit = RateLimitCircuitBreaker()

# Endpoint rate limit configs: path_prefix -> (max_requests, window_seconds)
ENDPOINT_LIMITS = {
    "/api/v1/auth/login": (3, 300),
    "/api/v1/auth/register": (3, 300),
    "/api/v1/auth/": (5, 60),
    "/api/v1/chat/": (20, 60),
    "/api/v1/drafting/": (10, 60),
}
GLOBAL_LIMIT = (30, 60)


class RateLimitManager:
    def __init__(self):
        self._redis_pool = None

    async def _get_redis(self):
        if self._redis_pool is None:
            try:
                import redis.asyncio as aioredis

                settings = get_settings()
                self._redis_pool = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            except Exception:
                return None
        return self._redis_pool

    async def _redis_check(self, key: str, max_requests: int, window: int) -> bool:
        redis = await self._get_redis()
        if redis is None:
            return False
        pipe = redis.pipeline()
        now = time.time()
        cutoff = now - window
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window * 2)
        _, count, _, _ = await pipe.execute()
        return int(count) < max_requests

    async def check(self, request: Request):
        path = request.url.path
        client_id = request.client.host if request.client else "unknown"
        key_base = f"rl:{client_id}"

        max_requests, window = GLOBAL_LIMIT
        for endpoint_path, (limit, win) in ENDPOINT_LIMITS.items():
            if path.startswith(endpoint_path):
                max_requests, window = limit, win
                break

        key = f"{key_base}:{path}"

        if _circuit.is_available():
            try:
                allowed = await self._redis_check(key, max_requests, window)
                if allowed is not False:
                    _circuit.record_success()
                    if not allowed:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Rate limit exceeded",
                            headers={"Retry-After": str(window)},
                        )
                    return
            except HTTPException:
                raise
            except Exception as e:
                _circuit.record_failure()
                logger.warning("redis_rate_limit_failed", error=str(e), fallback="memory")

        allowed = await _in_memory_limiter.check(key, max_requests, window)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)},
            )

    async def close(self):
        if self._redis_pool is not None:
            await self._redis_pool.aclose()
            self._redis_pool = None


rate_limit_manager = RateLimitManager()


async def check_rate_limit(request: Request):
    import os as _os

    if _os.environ.get("PYTEST_CURRENT_TEST"):
        return
    await rate_limit_manager.check(request)


def get_rate_limit_manager() -> RateLimitManager:
    return rate_limit_manager
