"""
Asyncpg connection pool.

This file is responsible for:
- Creating the Postgres connection pool
- Enforcing pool limits
- Handling safe shutdown

Every DB query in the app goes through this pool.
"""

import asyncpg
import logging

from backend.core.config import (
    DB_POOL_MIN_SIZE,
    DB_POOL_MAX_SIZE,
)

logger = logging.getLogger("db.pool")


# ============================
# Pool creation
# ============================

async def create_pool(database_url: str) -> asyncpg.Pool:
    """
    Create and return a Postgres connection pool.

    Called once at app startup.
    """
    try:
        pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=DB_POOL_MIN_SIZE,
            max_size=DB_POOL_MAX_SIZE,
            command_timeout=30,  # safety for runaway queries
        )
        logger.info("Postgres pool created (min=%s max=%s)", DB_POOL_MIN_SIZE, DB_POOL_MAX_SIZE)
        return pool
    except Exception as exc:
        logger.exception("Failed to create Postgres pool")
        raise


# ============================
# Pool shutdown
# ============================

async def close_pool(pool: asyncpg.Pool) -> None:
    """
    Gracefully close the Postgres pool.
    Called on server shutdown.
    """
    try:
        await pool.close()
        logger.info("Postgres pool closed")
    except Exception:
        logger.exception("Error while closing Postgres pool")
