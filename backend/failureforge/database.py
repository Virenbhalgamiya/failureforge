"""Database session management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from failureforge.config import get_settings
from failureforge.models import Base


_async_engine = None
_async_session_factory = None
_sync_engine = None
_sync_session_factory = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        settings = get_settings()
        _async_engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
        )
    return _async_engine


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        _sync_engine = create_engine(
            settings.database_url_sync,
            echo=settings.debug,
            connect_args={"check_same_thread": False} if "sqlite" in settings.database_url_sync else {},
        )
    return _sync_engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_async_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _async_session_factory


def get_sync_session_factory():
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(bind=get_sync_engine(), expire_on_commit=False)
    return _sync_session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Get a synchronous database session."""
    factory = get_sync_session_factory()
    return factory()


async def create_tables() -> None:
    """Create all tables."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_tables_sync() -> None:
    """Create all tables synchronously."""
    engine = get_sync_engine()
    Base.metadata.create_all(engine)
