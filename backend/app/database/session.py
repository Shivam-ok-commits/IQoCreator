"""Database engine, session management, and FastAPI dependency injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings


def create_engine() -> Any:
    """Create the async SQLAlchemy engine from application settings.

    Uses NullPool in testing to ensure connections are not reused
    across test cases. In development/production, uses the configured
    pool settings.
    """
    engine_kwargs: dict[str, Any] = {
        "echo": settings.database_echo,
        "pool_pre_ping": settings.database_pool_pre_ping,
    }

    if settings.is_testing:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.database_pool_size
        engine_kwargs["max_overflow"] = settings.database_max_overflow

    return create_async_engine(
        str(settings.database_url),
        **engine_kwargs,
    )


# Engine instance
engine = create_engine()

# Session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
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
