"""
Cache invalidation utilities.

Deletes all keys under a namespace using:
- SCAN (non-blocking)
- UNLINK (non-blocking delete)

Never uses KEYS.
Safe for large Redis instances.
"""

import asyncio
import logging
from typing import Iterable

from backend.core.config import CACHE_SCAN_BATCH, CACHE_DELETE_CHUNK, REDIS_OP_TIMEOUT

logger = logging.getLogger("cache.invalidate")


async def _unlink_chunked(redis, keys: Iterable[str]) -> None:
    keys = list(keys)
    if not keys:
        return

    for i in range(0, len(keys), CACHE_DELETE_CHUNK):
        chunk = keys[i : i + CACHE_DELETE_CHUNK]
        try:
            if hasattr(redis, "unlink"):
                await asyncio.wait_for(redis.unlink(*chunk), REDIS_OP_TIMEOUT)
            else:
                await asyncio.wait_for(redis.delete(*chunk), REDIS_OP_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("Redis unlink timeout for chunk starting %s", chunk[0])
        except Exception:
            logger.exception("Redis unlink error for chunk starting %s", chunk[0])


#main function to call
async def invalidate_namespace(redis, namespace: str) -> None:
    """
    Delete all Redis keys under namespace:*.

    Used after insert/update/delete to prevent stale reads.
    """
    try:
        cursor = 0
        while True:
            cursor, keys = await asyncio.wait_for(
                redis.scan(cursor=cursor, match=f"{namespace}:*", count=CACHE_SCAN_BATCH),
                REDIS_OP_TIMEOUT,
            )

            if keys:
                # redis may return bytes
                normalized = [
                    k.decode() if isinstance(k, (bytes, bytearray)) else k
                    for k in keys
                ]
                await _unlink_chunked(redis, normalized)

            if cursor == 0:
                break

    except asyncio.TimeoutError:
        logger.warning("Redis SCAN timeout during cache invalidation")
    except Exception:
        logger.exception("Redis SCAN error during cache invalidation")
