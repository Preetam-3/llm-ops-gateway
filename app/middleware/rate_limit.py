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

        # Key-based rate limit
        api_key = request.headers.get("Authorization", "").removeprefix("Bearer ")
        key_key = f"rate_limit:key:{api_key}"
        current = await self.redis.get(key_key)
        if current is not None and int(current) >= settings.max_requests_per_minute:
            llm_rate_limited_total.inc()
            raise HTTPException(status_code=429, detail="Rate limit exceeded (key)")
        await self.redis.incr(key_key)
        await self.redis.expire(key_key, 60, nx=True)

        # IP-based rate limit
        client_ip = request.client.host if request.client else "unknown"
        ip_key = f"rate_limit:ip:{client_ip}"
        ip_current = await self.redis.get(ip_key)
        if ip_current is not None and int(ip_current) >= settings.max_requests_per_minute_per_ip:
            llm_rate_limited_total.inc()
            raise HTTPException(status_code=429, detail="Rate limit exceeded (IP)")
        await self.redis.incr(ip_key)
        await self.redis.expire(ip_key, 60, nx=True)


rate_limiter = TokenBucketRateLimiter()
