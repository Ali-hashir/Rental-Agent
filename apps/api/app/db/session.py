"""Database session management."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..core.config import settings

connect_args: dict[str, object] = {}
if settings.database_ssl_required:
    connect_args["ssl"] = True

engine = create_async_engine(
    settings.database_async_url,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to provide an async session."""

    async with SessionLocal() as session:
        yield session
