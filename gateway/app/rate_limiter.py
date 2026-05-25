import time
import redis.asyncio as aioredis
from app.config import settings

class TokenBucketLimiter:
    def __init__(self):
        # Initialize connection to your running Docker Redis instance
        self.redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", 
            decode_responses=True
        )

    async def is_rate_limited(self, client_id: str) -> tuple[bool, int]:
        """
        Checks rate limiting using a fixed-window token-bucket variant in Redis.
        Returns: (is_limited, retry_after_seconds)
        """
        # Calculate a distinct tracking window for the current calendar minute
        current_window = int(time.time() / 60)
        redis_key = f"rate_limit:{client_id}:{current_window}"

        # Atomic execution block using a Redis pipeline sequence
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incrby(redis_key, 1)
            pipe.expire(redis_key, 60)
            request_count, _ = await pipe.execute()

        # Evaluate current request count against our threshold bounds
        if request_count > settings.DEFAULT_RATE_LIMIT_RPM:
            # Calculate remaining seconds left in the current minute window block
            retry_after = 60 - (int(time.time()) % 60)
            return True, retry_after

        return False, 0

# Create the singleton instance used by chat.py
limiter = TokenBucketLimiter()