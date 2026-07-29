import asyncio

from app.logging import get_logger

logger = get_logger(__name__)


class RetryHandler:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def execute(self, coro_factory, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await coro_factory(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2**attempt)
                logger.warning("retry_attempt", attempt=attempt + 1, max=self.max_retries, delay=delay, error=str(e))
                await asyncio.sleep(delay)
