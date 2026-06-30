from app.config import settings
from app.metrics.collectors import llm_rate_limited_total
from fastapi import Request, HTTPException
import redis.asyncio as aioredis


class TokenBucketRateLimiter:
    def __init__(self) -> None:
        self.redis: aioredis.Redis | None = None

    async def init(self) -> None:
        self.redis = aioredis.from_url(settings.redis_url)

    async def check(self, request: Request) -> None:
        if self.redis is None:
            return  # redis unavailable, allow through
        api_key = request.headers.get("Authorization", "").removeprefix("Bearer ")
        key = f"rate_limit:{api_key}"
        current = await self.redis.get(key)
        if current is not None and int(current) >= settings.max_requests_per_minute:
            llm_rate_limited_total.inc()
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        await self.redis.incr(key)
        await self.redis.expire(key, 60, nx=True)


rate_limiter = TokenBucketRateLimiter()
