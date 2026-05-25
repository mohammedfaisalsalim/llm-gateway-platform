import time
import logging
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger("uvicorn.error")

class SlidingWindowLimiter:
    def __init__(self):
        # Initialize connection pool to the Docker Redis instance
        self.redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", 
            decode_responses=True
        )

    async def is_rate_limited(self, client_id: str) -> tuple[bool, int]:
        """
        Sliding Window Rate Limiter using Redis Sorted Sets (zset).
        Guards against boundary burst exploits and fails open if Redis goes down.
        """
        try:
            now = time.time()
            window_start = now - 60  # Look back exactly 1 rolling minute
            redis_key = f"sliding_limit:{client_id}"

            # Atomic execution via Redis Pipeline
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(redis_key, 0, window_start)  # Drop expired hits
                pipe.zadd(redis_key, {str(now): now})              # Log current hit
                pipe.zcard(redis_key)                              # Count hits in window
                pipe.expire(redis_key, 60)                         # Keep key memory clean
                _, _, count, _ = await pipe.execute()

            # Check if client crossed the operational threshold
            if count > settings.DEFAULT_RATE_LIMIT_RPM:
                retry_after = 60 - int(now % 60)
                return True, retry_after

            return False, 0

        except Exception as e:
            # PRODUCTION HYGIENE: Fail open if Redis drops. Do not crash the gateway.
            logger.error(f"Rate Limiter Degraded (Redis Connection Failure): {str(e)}")
            return False, 0

# Singleton architecture instance
limiter = SlidingWindowLimiter()