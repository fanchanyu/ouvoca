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
    # JWT secret check — ALWAYS run, regardless of DEBUG
    jwt_is_default = ("change-me" in settings.JWT_SECRET or len(settings.JWT_SECRET) < 32)
    if jwt_is_default and not settings.ALLOW_DEMO_BYPASS:
        log.error("🚨 JWT_SECRET 是預設值或太短，且 ALLOW_DEMO_BYPASS=False")
        log.error("  立刻執行：openssl rand -hex 32  → 寫進 backend/.env")
        log.error("  或本機演練：設 ALLOW_DEMO_BYPASS=true（不建議生產用）")
        raise SystemExit(1)
    elif jwt_is_default:
        log.warning("⚠️ JWT_SECRET 是預設值；ALLOW_DEMO_BYPASS 已開啟，僅限測試/演練。")

    # Production-only checks
    if not settings.DEBUG:
        fatal_errors: list[str] = []

        if "*" in settings.CORS_ORIGINS:
            fatal_errors.append(
                "CORS_ORIGINS 含 '*'。production 必須改為明確 domain，例如：\n"
                "  CORS_ORIGINS=https://app.example.com,https://api.example.com"
            )

        # C4 修復：production 用 SQLite = 多人並發災難（database is locked + 資料遺失）
        # 升級為 FATAL，從啟動就擋下來，而不是只 log 一行 warning 沒人看到。
        if settings.DATABASE_DRIVER == "sqlite":
            fatal_errors.append(
                "DATABASE_DRIVER=sqlite 不能用於 production（多人並發會丟資料 + database locked 錯誤）。\n"
                "  改用 PostgreSQL：DATABASE_DRIVER=postgresql + DATABASE_URL_PROD=postgresql+asyncpg://...\n"
                "  或為單人 demo 環境設 DEBUG=true"
            )

        if fatal_errors:
            log.error("🚨 FATAL production config errors:")
            for i, e in enumerate(fatal_errors, 1):
                log.error("  %d) %s", i, e)
            log.error("拒絕啟動以保護資料。如為本機演練：設 DEBUG=true。")
            raise SystemExit(1)

    # auto-create tables when running on SQLite dev or first prod boot
    from app.database import init_db, AsyncSessionLocal
    await init_db()

    # Startup DB connectivity check — fail fast with clear message
    try:
        from sqlalchemy import text as _sql_text
        async with AsyncSessionLocal() as _probe_session:
            await _probe_session.execute(_sql_text("SELECT 1"))
        log.info("✅ DB 連線正常")
    except Exception as _db_exc:
        log.critical(
            "🚨 DB 無法連線！請確認 DATABASE_URL 設定是否正確。\n"
            "  SQLite: 確認 backend/ 目錄有寫入權限\n"
            "  PostgreSQL: 確認 DATABASE_URL_PROD 和資料庫服務運行中\n"
            "  錯誤詳情: %s", _db_exc
        )
        raise SystemExit(1)

    # register event rules (idempotent)
    import app.events  # noqa: F401
    import app.agents  # noqa: F401

    # Tenant 雙向防線：
    #   ① 寫入自動填 tenant_id
    #   ② 讀取自動加 WHERE tenant_id（覆蓋所有 87 endpoint，不必手動套）
    from app.core.tenant_context import (
        install_tenant_auto_injection, install_auto_tenant_filter,
    )
    install_tenant_auto_injection()
    install_auto_tenant_filter()

    # v3.16：自動把業務事件記到 CRM timeline（小白不必手動加 activity log）
    from app.services.crm_auto_log import install_auto_crm_logging
    install_auto_crm_logging()

    # v3.22：多階審批工作流 — 訂閱 po/so/payment.created 自動 evaluate 規則
    from app.services.approval import install_approval_hooks
    install_approval_hooks()

    # v3.25：家規 (House Rules) — 灌預設規則（idempotent，含「WO 釋放需有做法」）
    # v3.46：Glossary DB 載入（Phase 2 G-201，重啟後同義詞不丟失）
    from app.services.policy_engine import install_default_rules
    from app.agents.glossary import db_load_glossary
    async with AsyncSessionLocal() as _db:
        try:
            await install_default_rules(_db, tenant_id="HQ")
        except Exception as exc:
            log.warning("install_default_rules failed: %s", exc)
        try:
            n = await db_load_glossary(_db)
            if n:
                log.info("Glossary: loaded %d term(s) from DB", n)
        except Exception as exc:
            log.warning("db_load_glossary failed (first boot?): %s", exc)

    # ConfirmCard pending dict 背景 GC（v3.7）：
    # 防止過期 card 的 executor closure 持續持有 db session 而 OOM。
    # 每 60 秒掃一次；無人叫 /pending 時也保證會清。
    import asyncio as _asyncio
    from app.agents.confirm_card import _gc_expired

    async def _confirm_card_gc_loop():
        while True:
            try:
                await _gc_expired()
            except Exception as exc:
                log.warning("ConfirmCard GC loop error: %s", exc)
            await _asyncio.sleep(60)

    gc_task = _asyncio.create_task(_confirm_card_gc_loop(), name="confirm-card-gc")

    # v3.62：排程備份（審計 P1-7）— 依 system_settings 的
    # backup.enabled / backup.schedule（HH:MM）/ backup.retention_days 執行。
    async def _backup_scheduler():
        from app.services.system_settings import get_setting
        from app.services import backup as _backup

        while True:
            try:
                from app.database import AsyncSessionLocal as _SessionLocal
                async with _SessionLocal() as _sess:
                    enabled = bool(await get_setting(_sess, "backup.enabled", True))
                if enabled:
                    async with _SessionLocal() as _sess:
                        schedule = str(await get_setting(_sess, "backup.schedule", "03:00") or "03:00")
                        retention = int(await get_setting(_sess, "backup.retention_days", 30) or 30)
                    from datetime import datetime as _dt
                    hh, mm = (schedule.split(":") + ["00"])[:2]
                    target = _dt.now().replace(
                        hour=int(hh), minute=int(mm), second=0, microsecond=0,
                    )
                    if target <= _dt.now():
                        # 健檢 #16：用 timedelta 而非 replace(day+1) —
                        # 後者每逢月底會 ValueError（如 8/31 → day 32）
                        from datetime import timedelta as _td
                        target = target + _td(days=1)
                    wait_seconds = (target - _dt.now()).total_seconds()
                    await _asyncio.sleep(min(wait_seconds, 3600))  # 每小時檢查一次
                    # 到達排程時間視窗（±5 分鐘）才執行
                    if abs((target - _dt.now()).total_seconds()) < 300:
                        async with _SessionLocal() as _sess:
                            await _backup.create_backup(_sess, reason="scheduled")
                        removed = _backup.cleanup_old_backups(retention)
                        if removed:
                            log.info("Backup retention cleaned %d old backup(s)", removed)
                        await _asyncio.sleep(60)  # 執行後休息避免重複觸發
                else:
                    await _asyncio.sleep(3600)
            except _asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("Backup scheduler error: %s", exc)
                await _asyncio.sleep(3600)

    backup_task = _asyncio.create_task(_backup_scheduler(), name="backup-scheduler")

    yield

    gc_task.cancel()
    try:
        await gc_task
    except _asyncio.CancelledError:
        pass
    backup_task.cancel()
    try:
        await backup_task
    except _asyncio.CancelledError:
        pass
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

# Middleware execution order in Starlette is LIFO: last added runs first.
# 外層（最先跑）→ CORS → SecurityHeaders → RequestID → Auth → AiRateLimit → Audit → handler
app.add_middleware(AuditMiddleware)
# v3.42 R4：per-user AI 用量限制（每人每日 N 次）
from app.core.ai_rate_limit import AiRateLimitMiddleware
app.add_middleware(AiRateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
# 健檢 #10：CORS 必須是最外層 — 預檢 OPTIONS 不帶 Authorization，
# 若 CORS 在 Auth 內層，跨網域請求會被 Auth 401 且無 CORS header，瀏覽器全擋。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- routers ---
from app.api import (
    auth, inventory, purchase, production, chat,
    sales, quality, mps_mrp, accounting, warehouse, crm, events,
    permission, mesh, analytics, tax_tw, confirm_card, email_digest,
    agents_exec, reports, onboarding, files, llm_status,
    approval, policy,
    print_export,  # v3.36 PDF 列印 + CSV/Excel 匯出
    chat_feedback,  # v3.41 P7 chat thumbs up/down
    external_connections,  # v3.60 G-510 外部 DB 連接管理
    system_settings,  # M1-3 系統組態
    backups,  # v3.62 備份管理
)

app.include_router(chat.router)
app.include_router(confirm_card.router)
app.include_router(email_digest.router)
app.include_router(agents_exec.router)
app.include_router(reports.router)
app.include_router(onboarding.router)
app.include_router(files.router)
app.include_router(llm_status.router)
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
app.include_router(approval.router)
app.include_router(policy.router)
app.include_router(print_export.print_router)
app.include_router(print_export.export_router)
app.include_router(chat_feedback.router)
app.include_router(external_connections.router)
app.include_router(system_settings.router)
app.include_router(backups.router)


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
