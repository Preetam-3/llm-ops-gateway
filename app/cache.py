"""Response caching for LLM requests using Redis."""

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


_redis: aioredis.Redis | None = None


async def init_cache() -> None:
    """Initialize Redis connection for caching."""
    global _redis
    try:
        _redis = aioredis.from_url(settings.redis_url)
        await _redis.ping()
    except Exception:
        logger.warning("Cache unavailable — running without response caching")
        _redis = None


async def close_cache() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


def _cache_key(model: str, messages: list) -> str:
    """Generate a deterministic cache key from model name and messages."""
    raw = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return f"llm_cache:{hashlib.sha256(raw.encode()).hexdigest()}"


async def cache_get(model: str, messages: list) -> dict | None:
    """Retrieve cached response. Returns None if miss or cache disabled."""
    if not settings.cache_enabled or _redis is None:
        return None
    try:
        key = _cache_key(model, messages)
        data = await _redis.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


async def cache_set(model: str, messages: list, response: dict) -> None:
    """Store response in cache with TTL."""
    if not settings.cache_enabled or _redis is None:
        return
    try:
        key = _cache_key(model, messages)
        await _redis.setex(key, settings.cache_ttl_seconds, json.dumps(response))
    except Exception:
        pass


async def cache_clear() -> int:
    """Clear all cached LLM responses. Returns count of cleared keys."""
    if _redis is None:
        return 0
    count = 0
    cursor = 0
    while True:
        cursor, keys = await _redis.scan(cursor=cursor, match="llm_cache:*")
        if keys:
            await _redis.delete(*keys)
            count += len(keys)
        if cursor == 0:
            break
    return count
