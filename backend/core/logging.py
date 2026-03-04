# logging configuration will live here

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# -----------------------------
# Config values (env based)
# -----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()  # "json" or "text"
APP_NAME = os.getenv("APP_NAME", "backend")


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter for production.

    Example output:
    {
      "ts": "2026-01-15T10:20:30.123Z",
      "level": "INFO",
      "logger": "cache",
      "msg": "Cache hit",
      "app": "backend",
      "request_id": "abc123",
      "extra": {"key": "grocery:list"}
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "app": APP_NAME,
        }

        # Add request_id if present
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Add any extra fields (safe)
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload["extra"] = extra

        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """
    Human-friendly formatter for local dev.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        base = f"{ts} [{record.levelname}] {record.name}: {record.getMessage()}"

        request_id = getattr(record, "request_id", None)
        if request_id:
            base += f" request_id={request_id}"

        extra = getattr(record, "extra", None)
        if isinstance(extra, dict) and extra:
            base += f" extra={extra}"

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        return base


def _get_formatter() -> logging.Formatter:
    if LOG_FORMAT == "text":
        return TextFormatter()
    return JsonFormatter()


def setup_logging() -> None:
    """
    Call this ONCE at app startup.

    - Configures root logger
    - Ensures uvicorn logs follow same formatting
    """
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Remove any existing handlers (avoid duplicate logs on reload)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(_get_formatter())
    root.addHandler(handler)

    # Make noisy loggers less noisy
    logging.getLogger("asyncio").setLevel("WARNING")
    logging.getLogger("uvicorn.error").setLevel(LOG_LEVEL)
    logging.getLogger("uvicorn.access").setLevel("INFO")

    # Optional: reduce spam from redis/asyncpg libs if needed
    logging.getLogger("redis").setLevel("WARNING")
    logging.getLogger("asyncpg").setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    """
    Use this in files:
        logger = get_logger("cache")
    """
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: int,
    msg: str,
    *,
    request_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    """
    Small helper to keep logs consistent.

    Example:
        log_event(logger, logging.INFO, "Cache hit", extra={"key": key})
    """
    logger.log(
        level,
        msg,
        extra={
            "request_id": request_id,
            "extra": extra or {},
        },
        exc_info=exc_info,
    )
