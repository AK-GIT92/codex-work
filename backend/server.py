# ---------------------------------------
# Load .env
# ---------------------------------------
from dotenv import load_dotenv
load_dotenv()

import os
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from backend.db.pool import create_pool, close_pool
from backend.cache.redis import create_redis, close_redis
from backend.schema import schema

from fastapi.responses import JSONResponse
from backend.core.security import verify_access_token


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# ---------------------------------------
# ENV / CONFIG
# ---------------------------------------
ENV = os.getenv("ENV", "prod")  # dev / prod
RATE_LIMIT_MAX_REQ = int(os.getenv("RATE_LIMIT_MAX_REQ", "30"))
RATE_LIMIT_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))
REDIS_OP_TIMEOUT = float(os.getenv("REDIS_OP_TIMEOUT", "2.0"))

# ============================
# JWT Auth Guard (Bearer Access Token)
# ============================

async def auth_guard(request: Request):
    auth = request.headers.get("authorization")

    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth.split(" ", 1)[1]

    verify_access_token(token)

# ============================
# JWT Auth Guard (Bearer Refresh Token)
# ============================



# ============================
# Rate Limiter (Redis)
# ============================

async def graphql_rate_limit(request: Request):
    redis = getattr(request.app.state, "redis", None)
    if not redis:
        return  # if redis not available, skip (dev safe)

    ip = request.client.host
    key = f"ratelimit:{ip}:/8124data"

    try:
        count = await asyncio.wait_for(redis.incr(key), timeout=REDIS_OP_TIMEOUT)

        if count == 1:
            await asyncio.wait_for(redis.expire(key, RATE_LIMIT_WINDOW_SEC), timeout=REDIS_OP_TIMEOUT)

        if count > RATE_LIMIT_MAX_REQ:
            raise HTTPException(status_code=429, detail="Too many requests")

    except HTTPException:
        raise
    except Exception:
        # Fail-open: if Redis fails, don't break your API
        return


# ============================
# Lifespan (startup + shutdown)
# ============================

@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    if not redis_url:
        raise RuntimeError("REDIS_URL not set")

    # Startup
    app.state.pool = await create_pool(database_url)
    app.state.redis = await create_redis(redis_url)

    logger.info("Backend started")

    try:
        yield
    finally:
        # Shutdown
        await close_pool(app.state.pool)
        await close_redis(app.state.redis)
        logger.info("Backend stopped")


app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def block_graphql_get(request: Request, call_next):
    if request.url.path == "/8124data" and request.method == "GET":
        return JSONResponse(status_code=404, content={"detail": "Data lost in the universe..."})
    return await call_next(request)


# ============================
# CORS (React / Mobile)
# ============================

allow_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

# Add production domains here
prod_origin = os.getenv("PROD_ORIGIN")
if prod_origin:
    allow_origins.append(prod_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================
# GraphQL Context
# ============================

async def get_context():
    return {
        "pool": app.state.pool,
        "redis": app.state.redis,
    }


# ============================
# GraphQL Router
# ============================

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
    graphiql=(ENV != "prod"),
)

router = APIRouter()

# Protect BOTH GET + POST on /8124data
router.include_router(
    graphql_app,
    prefix="/8124data",
    dependencies=[Depends(auth_guard), Depends(graphql_rate_limit)],
)

app.include_router(router)
