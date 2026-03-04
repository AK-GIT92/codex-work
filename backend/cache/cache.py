"""
Safe Redis cache helpers.

All Redis access must go through these functions.
They provide:
- Timeouts
- Safe decoding
- Error isolation
"""

import asyncio
import logging
from typing import Optional

from backend.core import REDIS_OP_TIMEOUT

logger = logging.getLogger("cache")


# ============================
# Get
# ============================

async def cache_get(redis, key: str) -> Optional[str]:
    try:
        return await asyncio.wait_for(redis.get(key), REDIS_OP_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("Redis GET timeout for key=%s", key)
        return None
    except Exception:
        logger.exception("Redis GET failed for key=%s", key)
        return None


# ============================
# Set
# ============================

async def cache_set(redis, key: str, value: str, ttl: int) -> None:
    try:
        await asyncio.wait_for(redis.set(key, value, ex=ttl), REDIS_OP_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("Redis SET timeout for key=%s", key)
    except Exception:
        logger.exception("Redis SET failed for key=%s", key)
