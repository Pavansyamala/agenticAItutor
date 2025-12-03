# backend/app/utils/rate_limiter.py
import time
import logging
from functools import wraps
from typing import Callable, Any
import asyncio

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, calls_per_minute: int = 20):
        self.min_interval = 60.0 / calls_per_minute
        self.last_called = 0.0

    async def wait(self):
        now = time.time()
        elapsed = now - self.last_called
        to_wait = self.min_interval - elapsed
        if to_wait > 0:
            logger.info(f"Rate limit: sleeping {to_wait:.2f}s")
            await asyncio.sleep(to_wait)
        self.last_called = time.time()

# Global limiter (conservative for free tier)
limiter = RateLimiter(calls_per_minute=18)  # Safe: 18 RPM

def with_rate_limit(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        await limiter.wait()
        return await func(*args, **kwargs)
    return wrapper