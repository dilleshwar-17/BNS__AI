import functools
import time

from app.logging import get_logger

logger = get_logger(__name__)


class Decorators:
    @staticmethod
    def timing(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info("function_timing", func=func.__name__, elapsed=round(elapsed, 3))
            return result

        return wrapper
