import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from backend.core.config import JWT_SECRET, JWT_ALGO, JWT_EXP_MIN

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is required")

def create_access_token(payload: dict) -> str:
    payload = payload.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXP_MIN)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def create_refresh_token(payload: dict) -> str:
    payload = payload.copy()

    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=7)
    payload["type"] = "refresh"

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], leeway=30)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401,detail="Token expired")
    
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401,detail="Invalid Access token")
    

def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGO]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expired")

    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid Refresh token")
