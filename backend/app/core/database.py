"""Database configuration and session management"""

from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Convert PostgreSQL URL to async
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Async engine for FastAPI
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# Async session maker
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
)

# Sync session maker for migrations
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db():
    """
    Get synchronous database session (for migrations)
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

