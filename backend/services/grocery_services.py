"""
Business logic for Grocery.

- Validation
- Postgres queries
- Redis caching
- Cache stampede protection
- Cache invalidation

GraphQL resolvers MUST call functions here.
"""

import json
import asyncio
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

import asyncpg
from graphql import GraphQLError

from backend.core.config import (
    MAX_LIMIT,
    MAX_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_GROCERY_PRICE,
    CACHE_TTL_SECONDS,
    CACHE_NAMESPACE,
    DB_OP_TIMEOUT,
)

from backend.graphql.schema_types import Grocery, DeleteResult, SearchSuggestion, GroceryConnection, GroceryCursorSearch, GroceryCursorInput, GroceryCursor, GroceryFilteredConnection, GroceryFilterCursor, GroceryFilterCursorInput
from backend.cache.cache import cache_get, cache_set
from backend.cache.locks import acquire_lock, release_lock
from backend.cache.invalidate import invalidate_namespace
from backend.utils.pagination import normalize_pagination, paginated_cache_key


# ============================
# Helpers
# ============================

def _cache_key(limit: int) -> str:
    return f"{CACHE_NAMESPACE}:{limit}"


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise GraphQLError("Grocery name cannot be empty")
    if len(name) > MAX_NAME_LENGTH:
        raise GraphQLError("Grocery name too long")
    return name


def _validate_description(desc: Optional[str]) -> str:
    desc = desc or ""
    if len(desc) > MAX_DESCRIPTION_LENGTH:
        raise GraphQLError("Description too long")
    return desc


def _validate_price(price) -> Decimal:
    try:
        value = price if isinstance(price, Decimal) else Decimal(str(price))
    except Exception:
        raise GraphQLError("Invalid price")

    if value < 0 or value > MAX_GROCERY_PRICE:
        raise GraphQLError("Invalid price")

    return value


def _single_cache_key(grocery_id: int) -> str:
    return f"grocery:{grocery_id}"

def _search_cache_key(name: str) -> str:
    return f"grocery_search:{name.strip().lower()}"


# ============================
# Queries
# ============================

#display all grocery with limit
async def list_groceries(ctx, limit: int) -> List[Grocery]:
    if limit <= 0 or limit > MAX_LIMIT:
        raise GraphQLError("Invalid limit")

    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    key = _cache_key(limit)
    lock_key = f"{key}:lock"

    # ---------- Redis READ ----------
    if redis:
        cached = await cache_get(redis, key)
        if cached:
            print("⚡ Redis Read")
            data = json.loads(cached)
            return [
                Grocery(
                    groceryID=d["groceryID"],
                    groceryName=d["groceryName"],
                    groceryDescription=d["groceryDescription"],
                    groceryPrice=d["groceryPrice"],
                    groceryOrderTime=d["groceryOrderTime"]
                )
                for d in data
            ]

    # ---------- Stampede protection ----------
    token = None
    if redis:
        token = await acquire_lock(redis, lock_key)
        if not token:
            deadline = asyncio.get_event_loop().time() + 2
            while asyncio.get_event_loop().time() < deadline:
                cached = await cache_get(redis, key)
                if cached:
                    print("⚡ Redis stampede")
                    data = json.loads(cached)
                    return [
                        Grocery(
                            groceryID=d["groceryID"],
                            groceryName=d["groceryName"],
                            groceryDescription=d["groceryDescription"],
                            groceryPrice=d["groceryPrice"],
                            groceryOrderTime=d["groceryOrderTime"] 
                        )
                        for d in data
                    ]
                await asyncio.sleep(0.05)

    # ---------- DB ----------
    try:
        async with pool.acquire() as conn:
            rows = await asyncio.wait_for(
                conn.fetch(
                    "SELECT * FROM next_js_db.get_grocery_list($1)",
                    limit,
                ),
                DB_OP_TIMEOUT,
            )
    except Exception:
        raise GraphQLError("Database error")

    groceries = [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=r["grocery_price"],          
            groceryOrderTime=r["grocery_order_timde"],
        )
        for r in rows
    ]

    # ---------- Redis WRITE ----------
    if redis and token:
        print("⚡ Redis WRITE")
        await cache_set(
            redis,
            key,
            json.dumps([
                {
                    "groceryID": g.groceryID,
                    "groceryName": g.groceryName,
                    "groceryDescription": g.groceryDescription,
                    "groceryPrice": str(g.groceryPrice),
                    "groceryOrderTime": g.groceryOrderTime.isoformat(),
                }
                for g in groceries
            ]),
            CACHE_TTL_SECONDS,
        )
        await release_lock(redis, lock_key, token)

    return groceries



# display single grocery
async def get_grocery(ctx, id: int) -> Optional[Grocery]:
    if not id:
        raise GraphQLError("id required")

    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    key = _single_cache_key(id)
    lock_key = f"{key}:lock"

    # ---------- Redis READ ----------
    if redis:
        cached = await cache_get(redis, key)
        if cached:
            print("⚡ Redis HIT (single)")
            d = json.loads(cached)
            return Grocery(
                groceryID=d["groceryID"],
                groceryName=d["groceryName"],
                groceryDescription=d["groceryDescription"],
                groceryPrice=d["groceryPrice"],
                groceryOrderTime=d["groceryOrderTime"],
            )

    # ---------- Stampede protection ----------
    token = None
    if redis:
        token = await acquire_lock(redis, lock_key)
        if not token:
            # someone else is already rebuilding cache, wait a bit
            deadline = asyncio.get_event_loop().time() + 2
            while asyncio.get_event_loop().time() < deadline:
                cached = await cache_get(redis, key)
                if cached:
                    print("⚡ Redis stampede (single)")
                    d = json.loads(cached)
                    return Grocery(
                        groceryID=d["groceryID"],
                        groceryName=d["groceryName"],
                        groceryDescription=d["groceryDescription"],
                        groceryPrice=d["groceryPrice"],
                        groceryOrderTime=d["groceryOrderTime"],
                    )
                await asyncio.sleep(0.05)

    # ---------- DB ----------
    try:
        async with pool.acquire() as conn:
            row = await asyncio.wait_for(
                conn.fetchrow(
                    "SELECT * FROM next_js_db.get_grocery_details($1);",
                    id,
                ),
                DB_OP_TIMEOUT,
            )
    except Exception:
        raise GraphQLError("Database error")

    if not row:
        # release lock if we acquired it
        if redis and token:
            await release_lock(redis, lock_key, token)
        return None

    grocery = Grocery(
        groceryID=row["grocery_id"],
        groceryName=row["grocery_name"],
        groceryDescription=row["grocery_description"],
        groceryPrice=row["grocery_price"],
        groceryOrderTime=row["grocery_order_timde"],
    )

    # ---------- Redis WRITE ----------
    if redis and token:
        print("⚡ Redis WRITE (single)")
        await cache_set(
            redis,
            key,
            json.dumps({
                "groceryID": grocery.groceryID,
                "groceryName": grocery.groceryName,
                "groceryDescription": grocery.groceryDescription,
                "groceryPrice": str(grocery.groceryPrice),
                "groceryOrderTime": grocery.groceryOrderTime.isoformat(),
            }),
            CACHE_TTL_SECONDS,
        )
        await release_lock(redis, lock_key, token)

    return grocery



# display all groceries after search
async def search_grocery(ctx, name: str) -> List[Grocery]:
    if not name:
        raise GraphQLError("name required")

    name = name.strip()
    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    key = _search_cache_key(name)
    lock_key = f"{key}:lock"

    # Only cache "real" searches
    allow_cache = len(name) >= 3

    # ---------- Redis READ ----------
    if redis and allow_cache:
        cached = await cache_get(redis, key)
        if cached:
            print("⚡ Redis HIT (search)")
            data = json.loads(cached)
            return [
                Grocery(
                    groceryID=d["groceryID"],
                    groceryName=d["groceryName"],
                    groceryDescription=d["groceryDescription"],
                    groceryPrice=d["groceryPrice"],
                    groceryOrderTime=d["groceryOrderTime"],
                )
                for d in data
            ]

    # ---------- Stampede protection ----------
    token = None
    if redis and allow_cache:
        token = await acquire_lock(redis, lock_key)
        if not token:
            deadline = asyncio.get_event_loop().time() + 2
            while asyncio.get_event_loop().time() < deadline:
                cached = await cache_get(redis, key)
                if cached:
                    print("⚡ Redis stampede (search)")
                    data = json.loads(cached)
                    return [
                        Grocery(
                            groceryID=d["groceryID"],
                            groceryName=d["groceryName"],
                            groceryDescription=d["groceryDescription"],
                            groceryPrice=d["groceryPrice"],
                            groceryOrderTime=d["groceryOrderTime"],
                        )
                        for d in data
                    ]
                await asyncio.sleep(0.05)

    # ---------- DB ----------
    try:
        async with pool.acquire() as conn:
            rows = await asyncio.wait_for(
                conn.fetch(
                    "SELECT * FROM next_js_db.grocery_name_search($1);",
                    name,
                ),
                DB_OP_TIMEOUT,
            )
    except Exception:
        if redis and token:
            await release_lock(redis, lock_key, token)
        raise GraphQLError("Database error")

    groceries = [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=r["grocery_price"],
            groceryOrderTime=r["grocery_order_time"],
        )
        for r in rows
    ]

    # ✅ Cache ONLY when search is successful (has results)
    if redis and token and allow_cache and len(groceries) > 0:
        print("⚡ Redis WRITE (search success)")
        await cache_set(
            redis,
            key,
            json.dumps([
                {
                    "groceryID": g.groceryID,
                    "groceryName": g.groceryName,
                    "groceryDescription": g.groceryDescription,
                    "groceryPrice": str(g.groceryPrice),
                    "groceryOrderTime": g.groceryOrderTime.isoformat()
                    if hasattr(g.groceryOrderTime, "isoformat")
                    else str(g.groceryOrderTime),
                }
                for g in groceries
            ]),
            CACHE_TTL_SECONDS,
        )

    # Always release lock if acquired
    if redis and token:
        await release_lock(redis, lock_key, token)

    return groceries



# display all groceries after filter
async def grocery_filter(
    ctx,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    sortby: Optional[str] = None,
    sortorder: Optional[str] = None,
    sortdate: Optional[str] = None,
    sortprice: Optional[float] = None,
) -> List[Grocery]:

    pool: asyncpg.Pool = ctx["pool"]

    # Defaults
    limit = limit or 50
    offset = offset or 0
    sortby = sortby or "id"
    sortorder = (sortorder or "ASC").upper()

    # Validation
    if limit <= 0 or limit > MAX_LIMIT:
        raise GraphQLError("Invalid limit")
    if offset < 0:
        raise GraphQLError("Invalid offset")
    if sortorder not in ("ASC", "DESC"):
        raise GraphQLError("Invalid sortorder")
    if sortby not in ("id", "price", "time", "name"):
        raise GraphQLError("Invalid sortby")

    # Convert date string -> datetime (or None)
    dt_value = None
    if sortdate:
        try:
            dt_value = datetime.fromisoformat(sortdate.replace(" ", "T"))
        except Exception:
            raise GraphQLError("Invalid sortdate format")

    # Convert price -> Decimal (or None)
    price_value = None
    if sortprice is not None:
        try:
            price_value = Decimal(str(sortprice))
        except Exception:
            raise GraphQLError("Invalid sortprice")

    # ---------- DB ----------
    try:
        async with pool.acquire() as conn:
            rows = await asyncio.wait_for(
                conn.fetch(
                    """
                    SELECT * FROM next_js_db.get_grocery_filtered_list(
                        $1, $2, $3, $4, $5, $6
                    );
                    """,
                    limit,
                    offset,
                    sortby,
                    sortorder,
                    dt_value,
                    price_value,
                ),
                DB_OP_TIMEOUT,
            )
    except Exception:
        raise GraphQLError("Database error")

    return [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=r["grocery_price"],
            groceryOrderTime=r["grocery_order_timde"],
        )
        for r in rows
    ]
        

# display all groceries for autocomplete
async def searchSuggestions(ctx, name: str) -> List[SearchSuggestion]:
    name = (name or "").strip()

    if len(name) < 2:
        return []

    pool: asyncpg.Pool = ctx["pool"]

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM next_js_db.grocery_autocomplete($1, $2);",
                name,
                10
            )
    except Exception:
        raise GraphQLError("Database error")

    return [SearchSuggestion(groceryName=r["grocery_name"]) for r in rows]



#display all groceries with pagination
async def listGroceries(ctx, page: Optional[int] = None, page_size: Optional[int] = None) -> List[Grocery]:
    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    # ---------- Pagination ----------
    p = normalize_pagination(page, page_size)

    # Cache key like: grocery:list:page=1:size=20
    key = paginated_cache_key(CACHE_NAMESPACE, page=p.page, page_size=p.page_size)
    lock_key = f"{key}:lock"

    # ---------- Redis READ ----------
    if redis:
        cached = await cache_get(redis, key)
        if cached:
            print("⚡ Redis HIT (list)")
            data = json.loads(cached)
            return [
                Grocery(
                    groceryID=d["groceryID"],
                    groceryName=d["groceryName"],
                    groceryDescription=d["groceryDescription"],
                    groceryPrice=d["groceryPrice"],
                    groceryOrderTime=d["groceryOrderTime"],
                )
                for d in data
            ]

    # ---------- Stampede protection ----------
    token = None
    if redis:
        token = await acquire_lock(redis, lock_key)
        if not token:
            # Someone else is rebuilding the cache.
            # Wait briefly and retry cache reads.
            deadline = asyncio.get_event_loop().time() + 2
            while asyncio.get_event_loop().time() < deadline:
                cached = await cache_get(redis, key)
                if cached:
                    print("⚡ Redis stampede HIT (list)")
                    data = json.loads(cached)
                    return [
                        Grocery(
                            groceryID=d["groceryID"],
                            groceryName=d["groceryName"],
                            groceryDescription=d["groceryDescription"],
                            groceryPrice=d["groceryPrice"],
                            groceryOrderTime=d["groceryOrderTime"],
                        )
                        for d in data
                    ]
                await asyncio.sleep(0.05)

    # ---------- DB ----------
    try:
        async with pool.acquire() as conn:
            rows = await asyncio.wait_for(
                conn.fetch(
                    "SELECT * FROM next_js_db.get_grocery_list($1, $2);",
                    p.limit,
                    p.offset,
                ),
                DB_OP_TIMEOUT,
            )
    except Exception:
        if redis and token:
            await release_lock(redis, lock_key, token)
        raise GraphQLError("Database error")

    groceries = [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=str(r["grocery_price"]),
            groceryOrderTime=str(r["grocery_order_timde"]),
        )
        for r in rows
    ]

    # ---------- Redis WRITE ----------
    if redis and token:
        print("⚡ Redis WRITE (list)")
        await cache_set(
            redis,
            key,
            json.dumps(
                [
                    {
                        "groceryID": g.groceryID,
                        "groceryName": g.groceryName,
                        "groceryDescription": g.groceryDescription,
                        "groceryPrice": str(g.groceryPrice),
                        "groceryOrderTime": str(g.groceryOrderTime),
                    }
                    for g in groceries
                ]
            ),
            CACHE_TTL_SECONDS,
        )
        await release_lock(redis, lock_key, token)

    return groceries


#cursor pagination
async def listGroceriesCursor(
    ctx,
    limit: int = 20,
    cursor: Optional[int] = None,
) -> GroceryConnection:

    pool: asyncpg.Pool = ctx["pool"]

    try:
        async with pool.acquire() as conn:

            if cursor:
                rows = await conn.fetch(
                    """
                    SELECT * FROM next_js_db.get_grocery_cursor_list($2, $1);
                    """,
                    cursor,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM next_js_db.get_grocery_list($1)
                    """,
                    limit,
                )

    except Exception:
        raise GraphQLError("Database error")

    groceries = [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=str(r["grocery_price"]),
            groceryOrderTime=str(r["grocery_order_timde"]),
        )
        for r in rows
    ]

    # Determine next cursor
    next_cursor = groceries[-1].groceryID if len(groceries) == limit else None

    return GroceryConnection(
        items=groceries,
        nextCursor=next_cursor,
    )


#cursor pagination for search
async def searchGroceriesCursor(
    ctx,
    name: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[GroceryCursorInput] = None,
) -> GroceryCursorSearch:

    pool: asyncpg.Pool = ctx["pool"]

    cursor_time = None
    cursor_id = None

    if cursor:
        cursor_time = cursor.time
        cursor_id = cursor.id

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * 
                FROM next_js_db.grocery_name_cursor_search(
                    $1, $2, $3, $4
                )
                """,
                name,
                limit,
                cursor_time,
                cursor_id,
            )
    except Exception:
        raise GraphQLError("Database error")

    # Determine if next page exists
    has_next_page = len(rows) > limit

    if has_next_page:
        rows = rows[:-1]  # remove extra row

    groceries = [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=str(r["grocery_price"]),
            groceryOrderTime=str(r["grocery_order_timde"]), 
        )
        for r in rows
    ]

    next_cursor = None
    if has_next_page and rows:
        last = rows[-1]
        next_cursor = GroceryCursor(
            time=last["grocery_order_timde"],  
            id=last["grocery_id"],
        )

    return GroceryCursorSearch(
        items=groceries,
        nextCursor=next_cursor,
    )

#cursor pagination for filter
async def listGroceriesFilteredCursor(
    ctx,
    limit: int = 20,
    sort_by: str = "id",
    sort_order: str = "ASC",
    filter_datetime: Optional[datetime] = None,
    filter_price: Optional[float] = None,
    cursor: Optional[GroceryFilterCursorInput] = None,
) -> GroceryFilteredConnection:

    pool: asyncpg.Pool = ctx["pool"]

    cursor_value = None
    cursor_id = None

    if cursor:
        cursor_value = cursor.value
        cursor_id = cursor.id

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * 
                FROM next_js_db.get_grocery_cursor_filtered_list(
                    $1, $2, $3, $4, $5, $6, $7
                )
                """,
                limit,
                sort_by,
                sort_order,
                filter_datetime,
                filter_price,
                cursor_value,
                cursor_id,
            )
    except Exception:
        raise GraphQLError("Database error")

    has_next_page = len(rows) > limit

    if has_next_page:
        rows = rows[:-1]

    groceries = [
        Grocery(
            groceryID=r["grocery_id"],
            groceryName=r["grocery_name"],
            groceryDescription=r["grocery_description"],
            groceryPrice=str(r["grocery_price"]),
            groceryOrderTime=str(r["grocery_order_timde"]),
        )
        for r in rows
    ]

    next_cursor = None
    if has_next_page and rows:
        last = rows[-1]

        # determine correct sort value
        if sort_by == "price":
            sort_value = str(last["grocery_price"])
        elif sort_by == "time":
            sort_value = str(last["grocery_order_timde"])
        else:
            sort_value = str(last["grocery_id"])

        next_cursor = GroceryFilterCursor(
            value=sort_value,
            id=last["grocery_id"],
        )

    return GroceryFilteredConnection(
        items=groceries,
        nextCursor=next_cursor,
    )


# ============================
# Mutations
# ============================

async def add_grocery(ctx, grocery: str, description: str, price) -> Grocery:
    name = _validate_name(grocery)
    description = _validate_description(description)
    price = _validate_price(price)

    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM next_js_db.add_grocery($1, $2, $3)",
                    name,
                    description,
                    price,
                )
    except Exception:
        raise GraphQLError("Insert failed")

    if redis:
        # delete list cache namespace
        await invalidate_namespace(redis, "grocery_list")

    return Grocery(
        groceryID=row["grocery_id"],
        groceryName=row["grocery_name"],
        groceryDescription=row["grocery_description"],
        groceryPrice=row["grocery_price"],
        groceryOrderTime=row["grocery_order_timde"],
    )


async def edit_grocery(ctx, ID: int, grocery: str, description: str, price) -> Grocery:
    name = _validate_name(grocery)
    description = _validate_description(description)
    price = _validate_price(price)

    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM next_js_db.update_grocery($1, $2, $3, $4)",
                    ID,
                    name,
                    description,
                    price,
                )
    except Exception:
        raise GraphQLError("Update failed")

    if not row:
        raise GraphQLError("Not found")

    if redis:
        # delete single item cache
        await redis.delete(_single_cache_key(ID))

        # delete list cache namespace
        await invalidate_namespace(redis, "grocery_list")

        

    return Grocery(
        groceryID=row["grocery_id"],
        groceryName=row["grocery_name"],
        groceryDescription=row["grocery_description"],
        groceryPrice=row["grocery_price"],
        groceryOrderTime=row["grocery_order_timde"],
    )


async def delete_grocery(ctx, ID: int) -> DeleteResult:
    pool: asyncpg.Pool = ctx["pool"]
    redis = ctx.get("redis")

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM next_js_db.delete_grocery($1)",
                    ID,
                )
    except Exception:
        raise GraphQLError("Delete failed")

    if not row:
        raise GraphQLError("Not found")

    if redis:
        # delete single item cache
        await redis.delete(_single_cache_key(ID))

        # delete list cache namespace
        await invalidate_namespace(redis, "grocery_list")


    return DeleteResult(groceryID=row["grocery_id"])
