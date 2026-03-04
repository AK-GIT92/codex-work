"""
Redis client setup.

This module is responsible for:
- Creating the Redis connection
- Handling clean shutdown

Uses redis-py asyncio client.
"""

import logging
from redis.asyncio import Redis

logger = logging.getLogger("cache.redis")


# ============================
# Redis creation
# ============================

async def create_redis(redis_url: str) -> Redis:
    """
    Create and return a Redis client.
    Called once at app startup.
    """
    try:
        redis = Redis.from_url(
            redis_url,
            decode_responses=True,   # return str instead of bytes
            socket_timeout=2,
            socket_connect_timeout=2,
        )

        # Test connection
        await redis.ping()
        logger.info("Redis connected")

        return redis

    except Exception:
        logger.exception("Failed to connect to Redis")
        raise


# ============================
# Redis shutdown
# ============================

async def close_redis(redis: Redis):
    """
    Gracefully close Redis connection.
    """
    try:
        await redis.close()
        if hasattr(redis, "wait_closed"):
            await redis.wait_closed()
        logger.info("Redis closed")
    except Exception:
        logger.exception("Error while closing Redis")
