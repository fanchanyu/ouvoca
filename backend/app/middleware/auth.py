"""Authentication middleware.

Behaviour
---------
- Skips public paths (login, health, docs, SSE, root).
- Accepts `Authorization: Bearer <jwt>`.
- When `settings.demo_bypass_active` is true (JWT_SECRET still default),
  also accepts the literal token `demo` as a super-admin user — useful for
  local dev and frontend prototyping. Auto-disables when a real secret is set.
- Populates `request.state.user = {employee_id, username, roles, permissions}`.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import jwt, JWTError

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

PUBLIC_PATHS = {
    "/", "/api/health", "/api/auth/login",
    # Note: /api/auth/register is NOT public — handler enforces
    # require_permission("organization.user.read"). Listing it here
    # used to make register effectively unreachable (middleware skipped
    # token parsing → handler always got 401). Caught by smoke test.
    "/docs", "/redoc", "/openapi.json", "/favicon.ico",
}
# Factory node register / list are public for MVP (廠端啟動時自報).
# 生產環境應加 shared-secret header 或 mTLS 驗證 — TODO.
PUBLIC_PREFIXES = (
    "/api/events/",
    "/api/factory/",
    "/api/tax/tw/validate-tax-id",  # 純驗證算法，無 DB / 無敏感資料（含 /-countries 子路徑）
)


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


DEMO_USER = {
    "employee_id": "demo-admin",
    "username": "demo",
    "roles": ["admin", "manager", "purchaser", "planner", "sales", "inspector"],
    "permissions": ["*"],
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _is_public(path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()

        if not token:
            return JSONResponse(
                {"code": "missing_token", "detail": "缺少 Authorization 標頭"},
                status_code=401,
            )

        if settings.demo_bypass_active and token == "demo":
            request.state.user = DEMO_USER
            return await call_next(request)

        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            request.state.user = {
                "employee_id": payload.get("sub"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
            }
        except JWTError as exc:
            log.info("JWT decode failed: %s", exc)
            return JSONResponse(
                {"code": "invalid_token", "detail": "Token 無效或已過期"},
                status_code=401,
            )

        return await call_next(request)
