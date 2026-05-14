"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import register_exception_handlers
from app.core.rate_limit import limiter
from app.middleware import (
    AuditMiddleware, AuthMiddleware, RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

setup_logging(settings.LOG_LEVEL, settings.LOG_JSON)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s v%s | DB=%s | LLM=%s",
             settings.APP_NAME, settings.APP_VERSION,
             settings.DATABASE_DRIVER, settings.LLM_PROVIDER)
    if settings.demo_bypass_active:
        log.warning("⚠️  Demo bypass ACTIVE — Bearer 'demo' grants super-admin. "
                    "Set a real JWT_SECRET to disable.")
    # Production 環境安全檢查
    if not settings.DEBUG:
        if "*" in settings.CORS_ORIGINS:
            log.error("🔴 SECURITY: CORS_ORIGINS contains '*' in production. This is unsafe.")
        if "change-me" in settings.JWT_SECRET:
            log.error("🔴 SECURITY: JWT_SECRET is still default. RUN: openssl rand -hex 32")
        if settings.DATABASE_DRIVER == "sqlite":
            log.warning("⚠️  Using SQLite in non-debug mode. Consider PostgreSQL for multi-user.")

    # auto-create tables when running on SQLite dev or first prod boot
    from app.database import init_db
    await init_db()

    # register event rules (idempotent)
    import app.events  # noqa: F401
    import app.agents  # noqa: F401

    # Install tenant auto-injection（新建 ORM 物件自動帶 tenant_id）
    from app.core.tenant_context import install_tenant_auto_injection
    install_tenant_auto_injection()

    yield
    log.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Native Enterprise Resource Planning System",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

register_exception_handlers(app)

# ── Rate limiter ────────────────────────────────────────────
# slowapi 要求 app.state.limiter 設好，加 SlowAPIMiddleware，並注入 handler
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request, exc):
    """超量回 429 + 友善訊息 + Retry-After header。"""
    from starlette.responses import JSONResponse
    detail = f"Too many requests: {exc.detail}. 請稍候再試。"
    return JSONResponse(
        status_code=429,
        content={
            "code": "rate_limit_exceeded",
            "detail": detail,
            "limit": str(exc.detail) if exc.detail else None,
        },
        headers={"Retry-After": "60"},
    )

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Middleware execution order in Starlette is LIFO: last added runs first.
# Outermost (first to run) → SecurityHeaders → RequestID → Auth → Audit → handler.
# add 順序：Audit → Auth → RequestID → SecurityHeaders（最後加 = 最先跑 = 最外層）
app.add_middleware(AuditMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


# --- routers ---
from app.api import (
    auth, inventory, purchase, production, chat,
    sales, quality, mps_mrp, accounting, warehouse, crm, events,
    permission, mesh, analytics, tax_tw,
)

app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(auth.org_router)
app.include_router(inventory.router)
app.include_router(purchase.router)
app.include_router(production.router)
app.include_router(sales.router)
app.include_router(quality.router)
app.include_router(mps_mrp.router)
app.include_router(accounting.router)
app.include_router(warehouse.router)
app.include_router(crm.router)
app.include_router(events.router)
app.include_router(permission.router)
app.include_router(mesh.router)
app.include_router(analytics.router)
app.include_router(tax_tw.router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
