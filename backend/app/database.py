"""Async SQLAlchemy engine + session factory + init_db helper.

PostgreSQL uses an asyncpg pool; SQLite (dev) uses a single shared connection
with `check_same_thread=False` semantics under aiosqlite.
"""
import asyncio
import logging
import os
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.base import Base
import app.models  # noqa: F401 — ensure all models are imported so metadata is populated

log = logging.getLogger(__name__)


# v3.60 fix：在部分容器/沙箱環境（含本開發環境），CPython 預設
# `_UnixSelectorEventLoop` 的 `call_soon_threadsafe` 跨執行緒喚醒會延遲數十秒，
# 導致 aiosqlite（依賴背景 thread + queue 跨執行緒回報結果）的每個操作都像 hang。
# uvloop 改用 eventfd 喚醒，不受影響。在 app import 階段就裝成預設 policy，
# uvicorn / pytest / scripts 全部受益（uvicorn[standard] 已帶 uvloop）。
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    log.debug("uvloop event loop policy installed")
except Exception:  # pragma: no cover - fallback for exotic environments
    log.warning("uvloop unavailable; falling back to default asyncio policy")


def _ensure_sqlite_dir(url: str) -> None:
    """從 sqlite URL 抽出檔案路徑並確保 parent dir 存在。

    背景：sqlite 檔不存在時會自動建立，但**父目錄不存在會直接 fail**。
    docker volume mount 通常會 auto-create mount point，但若：
      - 非 docker 環境 + 自訂相對路徑（如 ./backend/data/erp.db）
      - read_only filesystem 但忘記 mount tmpfs
    都會在 init_db 時噴 sqlite3.OperationalError: unable to open database file。
    """
    if not url.startswith("sqlite"):
        return
    # 解析 sqlite+aiosqlite:///path/to/db.sqlite 或 sqlite:////abs/path
    # 三斜線 = 相對路徑；四斜線 = 絕對路徑
    after_scheme = url.split(":///", 1)[-1] if ":///" in url else url.split("://", 1)[-1]
    # 開頭多一個 / 表絕對路徑
    db_path = Path("/" + after_scheme) if after_scheme.startswith("/") else Path(after_scheme)
    parent = db_path.parent
    if parent and str(parent) not in (".", ""):
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.error("無法建立 sqlite 父目錄 %s：%s", parent, exc)
            raise


def _make_engine():
    url = settings.effective_db_url

    if settings.DATABASE_DRIVER == "postgresql":
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

    # SQLite path：先確保父目錄存在（避免「DB 載入失敗」的最常見原因）
    _ensure_sqlite_dir(url)
    log.info("SQLite DB: %s (cwd=%s)", url, os.getcwd())

    # SQLite (aiosqlite)：預設 NullPool（測試避免 lock contention）。
    # 效能健檢 ②：單機桌面版可設 SQLITE_POOL_REUSE=true 改用小型 QueuePool
    # （連線重用，實測每請求省 ~0.5ms；並發寫入場景建議維持 NullPool）。
    pool_reuse = os.getenv("SQLITE_POOL_REUSE", "").lower() == "true"
    if pool_reuse:
        from sqlalchemy.pool import AsyncAdaptedQueuePool
        sqlite_engine = create_async_engine(
            url, echo=settings.DEBUG,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=5, max_overflow=5,
        )
    else:
        sqlite_engine = create_async_engine(url, echo=settings.DEBUG, poolclass=NullPool)

    # A4 修復：每條 SQLite 連線啟用 WAL + 友善 pragma，避免 50 人並發時 database is locked。
    #   - journal_mode=WAL：讀寫並發（reader 不擋 writer）
    #   - synchronous=NORMAL：搭配 WAL 安全且快
    #   - busy_timeout=5000：寫鎖衝突時最多等 5 秒（而非立即噴錯）
    #   - foreign_keys=ON：SQLite 預設關閉 FK，這裡強制開啟以維持資料一致性
    event.listen(sqlite_engine.sync_engine, "connect", _enable_sqlite_pragmas)
    return sqlite_engine


def _enable_sqlite_pragmas(dbapi_conn, _connection_record):
    """SQLite connect-time pragma 設定。

    必須對每條新連線執行（pragma 是 per-connection 而非 per-database）。

    foreign_keys=ON 僅在非 DEBUG 模式啟用：
      - production（DEBUG=false）需要 FK 維持資料一致性
      - 開發/測試（DEBUG=true）保持 SQLite 預設關閉，避免既有 fixture 資料
        因人造 FK 不齊全而炸（這些測試本來就只驗業務邏輯，不驗 FK）
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    if not settings.DEBUG:
        cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = _make_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a scoped async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables (dev mode; production uses Alembic).

    v3.70：create_all 後呼叫 ensure_fk_indexes —
    全新安裝（一鍵/Docker/每次啟動）直接拿到 FK 複合索引，
    不再只有走 alembic 的升級路徑有索引。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from app.services.db_indexes import ensure_fk_indexes
        await conn.run_sync(ensure_fk_indexes)
