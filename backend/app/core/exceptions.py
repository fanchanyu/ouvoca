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

    # v3.35: 電腦小白友善 — 把 FastAPI 預設 HTTPException 之英文訊息中文化
    # 註：FastAPI 之 HTTPException 繼承自 Starlette；404 未定義路徑為 Starlette 拋出
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_req: Request, exc: StarletteHTTPException):
        # 友善訊息對照（針對 SMB 電腦小白）
        friendly_msg = {
            400: "請求格式有誤，請檢查輸入內容",
            401: "尚未登入或登入過期，請重新登入",
            403: "您沒有此功能的權限，請洽公司管理員 / 老闆",
            404: "找不到您要的資料",
            405: "不支援的操作方式",
            409: "資料衝突（可能重複或被他人修改）",
            413: "上傳檔案過大",
            415: "不支援的檔案格式",
            422: "資料格式不正確",
            429: "操作太頻繁，請稍候再試",
            500: "系統忙線中，請稍候再試；若持續發生請洽 IT",
            502: "服務暫不可用",
            503: "服務維護中",
            504: "回應逾時，請稍候再試",
        }
        # 保留 detail 若已是中文 / 自訂；否則用 friendly 對照
        detail_str = str(exc.detail or "")
        is_default_english = detail_str in (
            "Not Found", "Forbidden", "Unauthorized", "Method Not Allowed",
            "Internal Server Error", "Bad Request", "Conflict",
        )
        final_detail = friendly_msg.get(exc.status_code, detail_str) if is_default_english else detail_str
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"http_{exc.status_code}",
                "detail": final_detail,
                "original_detail": detail_str if is_default_english else None,
                "hint": friendly_msg.get(exc.status_code),
            },
        )

    @app.exception_handler(Exception)
    async def fallback_exc(_req: Request, exc: Exception):
        log.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "detail": "系統忙線中，請稍候再試；若持續發生請洽 IT",
            },
        )
