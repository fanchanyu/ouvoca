"""Async SQLAlchemy engine + session factory + init_db helper.

PostgreSQL uses an asyncpg pool; SQLite (dev) uses a single shared connection
with `check_same_thread=False` semantics under aiosqlite.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.base import Base
import app.models  # noqa: F401 — ensure all models are imported so metadata is populated


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
    # SQLite (aiosqlite): NullPool avoids lock contention in async tests
    return create_async_engine(url, echo=settings.DEBUG, poolclass=NullPool)


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
    """Create all tables (dev mode; production uses Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
