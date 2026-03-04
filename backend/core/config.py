"""
Global configuration for the backend.

This file contains:
- Limits (pagination, input sizes)
- Cache TTLs
- Database & Redis timeouts
- Namespace prefixes

Every service, cache layer, and resolver uses these values.
Change them here → entire system adapts.
"""
import os
from decimal import Decimal


# ============================
# PyJWT
# ============================

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = "HS256"
JWT_EXP_MIN = 100

# ============================
# Pagination & Query Limits
# ============================

# Max number of groceries returned in one request
MAX_LIMIT = 6000

# Default page size if frontend does not provide one
DEFAULT_LIMIT = 20

# Max offset to prevent deep pagination abuse
MAX_OFFSET = 10_000


# ============================
# Input Size Limits
# ============================

# Prevent attackers from sending huge payloads
MAX_NAME_LENGTH = 250
MAX_DESCRIPTION_LENGTH = 2_000

# Business safety: max allowed grocery price
MAX_GROCERY_PRICE = Decimal("1000000.00")   # 1 million


# ============================
# Redis Cache
# ============================

# How long grocery lists stay cached
CACHE_TTL_SECONDS = 300   # 5 minutes

# Namespace for grocery cache keys
CACHE_NAMESPACE = "grocery_list"

# How many keys to scan per Redis SCAN call
CACHE_SCAN_BATCH = 100

# Chunk size for cache deletion (avoid huge DEL)
CACHE_DELETE_CHUNK = 100


# ============================
# Timeouts (very important)
# ============================

# Max time we wait for Redis
REDIS_OP_TIMEOUT = 1.5   # seconds

# Max time we wait for Postgres
DB_OP_TIMEOUT = 5.0     # seconds


# ============================
# Database Pool
# ============================

# Asyncpg pool sizing (tune for Neon)
DB_POOL_MIN_SIZE = 5
DB_POOL_MAX_SIZE = 20


# ============================
# Sorting / Filtering Defaults
# ============================


# Default sorting
DEFAULT_SORT_FIELD = "time"
DEFAULT_SORT_DIRECTION = "desc"


# Redis
REDIS_URL = os.getenv("REDIS_URL")
REDIS_OP_TIMEOUT = float(os.getenv("REDIS_OP_TIMEOUT", "1.5"))

# Cache
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
CACHE_SCAN_BATCH = int(os.getenv("CACHE_SCAN_BATCH", "100"))
CACHE_DELETE_CHUNK = int(os.getenv("CACHE_DELETE_CHUNK", "100"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
DB_OP_TIMEOUT = float(os.getenv("DB_OP_TIMEOUT", "5.0"))

# Redis lock TTL to avoid stampede
CACHE_LOCK_TTL_SECONDS = int(DB_OP_TIMEOUT) + 2
