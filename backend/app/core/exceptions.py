"""Application-wide exception types & FastAPI handlers.

Throw these from services; the handlers below convert them to clean JSON.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.logging import get_logger

log = get_logger(__name__)


class AppException(Exception):
    """Base class for all custom app errors."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"


class BusinessRuleError(AppException):
    """ConstraintChecker BLOCK → 422 + structured payload."""

    status_code = 422
    code = "business_rule_blocked"


class PermissionDeniedError(AppException):
    status_code = 403
    code = "permission_denied"


class AuthenticationError(AppException):
    status_code = 401
    code = "authentication_failed"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exc(_req: Request, exc: AppException):
        log.warning("AppException %s: %s | extra=%s", exc.code, exc.message, exc.extra)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "detail": exc.message, **exc.extra},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exc(_req: Request, exc: IntegrityError):
        log.warning("IntegrityError: %s", exc)
        return JSONResponse(
            status_code=409,
            content={"code": "integrity_error", "detail": "資料衝突 (unique/FK 違反)", "raw": str(exc.orig)[:200]},
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_exc(_req: Request, exc: SQLAlchemyError):
        log.exception("Database error")
        return JSONResponse(
            status_code=500,
            content={"code": "db_error", "detail": "資料庫錯誤", "raw": str(exc)[:200]},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_req: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": "validation_error", "detail": "請求參數驗證失敗", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def fallback_exc(_req: Request, exc: Exception):
        log.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "detail": "系統內部錯誤"},
        )
