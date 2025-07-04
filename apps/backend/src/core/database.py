"""Database connection and session management using SQLAlchemy."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from src.core.config import settings

logger = logging.getLogger(__name__)

# Base class for ORM models
Base = declarative_base()

# Create async engine
engine = create_async_engine(
    settings.POSTGRES_URL,
    poolclass=NullPool,  # Use NullPool for async
    echo=False,  # Set to True for SQL logging
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    This context manager ensures proper session cleanup and transaction handling.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI to get database session.
    
    This is used with FastAPI's dependency injection system.
    """
    async with get_async_session() as session:
        yield session


class DatabaseManager:
    """Database connection and health management."""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
    
    async def check_health(self) -> bool:
        """Check database connection health."""
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with get_async_session() as session:
            yield session
    
    async def close(self):
        """Close the database engine."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()