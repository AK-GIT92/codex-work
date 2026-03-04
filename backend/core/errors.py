# core/errors.py
from typing import Optional


class AppError(Exception):
    """
    Base application error.
    All custom errors MUST inherit from this.
    """
    code: str = "APP_ERROR"
    message: str = "Application error"
    status_code: int = 500

    def __init__(self, message: Optional[str] = None):
        if message:
            self.message = message
        super().__init__(self.message)


# =========================
# Client / Request errors
# =========================

class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400
    message = "Invalid input provided"


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    message = "Resource not found"


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409
    message = "Resource conflict"


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401
    message = "Unauthorized access"


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403
    message = "Forbidden"


# =========================
# Infrastructure errors
# =========================

class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    status_code = 500
    message = "Database operation failed"


class CacheError(AppError):
    code = "CACHE_ERROR"
    status_code = 500
    message = "Cache operation failed"


class ExternalServiceError(AppError):
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502
    message = "External service failed"

