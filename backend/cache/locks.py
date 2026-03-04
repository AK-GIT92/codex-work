"""
Redis distributed locks.

Used to prevent cache stampede:
- Only one request rebuilds the cache
- Others wait for it

Uses token-based locking for safety.
"""

import asyncio
import uuid
import logging

from backend.core.config import REDIS_OP_TIMEOUT, CACHE_LOCK_TTL_SECONDS

logger = logging.getLogger("cache.locks")


# ============================
# Acquire Lock
# ============================

async def acquire_lock(redis, key: str) -> str | None:
    """
    Try to acquire a Redis lock.

    Returns:
      token (str) if acquired
      None if someone else holds it
    """
    token = str(uuid.uuid4())

    try:
        ok = await asyncio.wait_for(
            redis.set(key, token, ex=CACHE_LOCK_TTL_SECONDS, nx=True),
            REDIS_OP_TIMEOUT,
        )
        return token if ok else None

    except asyncio.TimeoutError:
        logger.warning("Redis lock timeout for key=%s", key)
        return None
    except Exception:
        logger.exception("Redis lock error for key=%s", key)
        return None


# ============================
# Release Lock (safe)
# ============================

_RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


async def release_lock(redis, key: str, token: str) -> None:
    """
    Release a Redis lock only if token matches.
    Prevents deleting someone else's lock.
    """
    try:
        await asyncio.wait_for(
            redis.eval(_RELEASE_SCRIPT, 1, key, token),
            REDIS_OP_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.warning("Redis unlock timeout for key=%s", key)
    except Exception:
        logger.exception("Redis unlock error for key=%s", key)
