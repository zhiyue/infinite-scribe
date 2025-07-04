"""
Database configuration and connection management.
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
        self.sync_session_factory = None
    
    def initialize(self, database_url: str):
        """Initialize database connections."""
        # Parse URL for async version
        if database_url.startswith('postgresql://'):
            async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        else:
            async_url = database_url
            
        # Configure connection pool for high concurrency
        pool_size = int(os.getenv('DB_POOL_SIZE', '20'))
        max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        
        # Create async engine with proper pool configuration
        self.engine = create_async_engine(
            async_url,
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
        )
        
        # Create session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create sync engine for migrations
        sync_url = database_url
        self.sync_engine = create_engine(
            sync_url,
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        self.sync_session_factory = sessionmaker(
            self.sync_engine,
            expire_on_commit=False
        )
        
        logger.info(f"Database initialized with pool_size={pool_size}, max_overflow={max_overflow}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
        if hasattr(self, 'sync_engine'):
            self.sync_engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


def get_database_url() -> str:
    """Get database URL from environment variables."""
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    database = os.getenv('DB_NAME', 'genesis')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


async def init_db():
    """Initialize database connection."""
    database_url = get_database_url()
    db_manager.initialize(database_url)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with db_manager.get_session() as session:
        yield session


async def close_db():
    """Close database connections."""
    await db_manager.close()