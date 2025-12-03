# backend/app/utils/rate_limiter.py
import asyncio
import time
from functools import wraps

class SimpleRateLimiter:
    def __init__(self, min_interval: float = 3.5):  # Safe for Groq free tier
        self.min_interval = min_interval
        self.last_called = 0.0

    async def wait(self):
        now = time.time()
        elapsed = now - self.last_called
        sleep_time = max(0, self.min_interval - elapsed)
        if sleep_time > 0:
            print(f"[Rate Limiter] Sleeping {sleep_time:.2f}s to avoid 429...")
            await asyncio.sleep(sleep_time)
        self.last_called = time.time()

# Global limiter
limiter = SimpleRateLimiter(min_interval=3.8)  # 15–16 calls per minute → safe

def with_rate_limit(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await limiter.wait()
        return await func(*args, **kwargs)
    return wrapper