"""
QueryPilot — Database Engine & Session Factory

Provides the async SQLAlchemy engine, session maker, and a FastAPI
dependency (`get_db`) that yields a session per request.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    settings.app_db_url,
    echo=(settings.log_level == "debug"),
    future=True,
)

# ── Session Factory ───────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative Base ─────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── FastAPI Dependency ────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    Yield an async database session.

    Usage in FastAPI endpoints:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Lifecycle ─────────────────────────────────────────────────
async def init_db():
    """Create all tables. Called on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine. Called on application shutdown."""
    await engine.dispose()
