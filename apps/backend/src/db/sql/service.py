"""PostgreSQL database connection service."""

import asyncio
import logging
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool

from src.core.config import settings

logger = logging.getLogger(__name__)


class PostgreSQLService:
    """Manages PostgreSQL database connections."""

    def __init__(self):
        self._pool: Pool | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Initialize connection pool."""
        async with self._lock:
            if self._pool is not None:
                return

            try:
                self._pool = await asyncpg.create_pool(
                    settings.database.postgres_url.replace("+asyncpg", ""),
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    max_inactive_connection_lifetime=300,
                )
                logger.info("PostgreSQL connection pool created successfully")
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL connection pool: {e}")
                raise

    async def disconnect(self) -> None:
        """Close connection pool."""
        async with self._lock:
            if self._pool is None:
                return

            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    async def check_connection(self) -> bool:
        """Check if database is accessible."""
        if self._pool is None:
            return False

        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"PostgreSQL connection check failed: {e}")
            return False

    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool."""
        if self._pool is None:
            await self.connect()

        assert self._pool is not None, "Pool should be initialized after connect()"
        async with self._pool.acquire() as conn:
            yield conn

    async def verify_schema(self) -> bool:
        """Verify required tables exist."""
        required_tables = [
            "novels",
            "chapters",
            "characters",
            "worldview_entries",
            "reviews",
            "story_arcs",
        ]

        try:
            async with self.acquire() as conn:
                existing_tables = await conn.fetch(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename = ANY($1::text[])
                    """,
                    required_tables,
                )

                existing_table_names = {row["tablename"] for row in existing_tables}
                missing_tables = set(required_tables) - existing_table_names

                if missing_tables:
                    logger.warning(f"Missing PostgreSQL tables: {missing_tables}")
                    return False

                logger.info("All required PostgreSQL tables exist")
                return True
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False

    async def execute(self, query: str, parameters: tuple | list | None = None):
        """Execute a SQL query with parameters."""
        if self._pool is None:
            await self.connect()

        async with self.acquire() as conn:
            if parameters:
                result = await conn.fetch(query, *parameters)
            else:
                result = await conn.fetch(query)
            return [dict(row) for row in result]


postgres_service = PostgreSQLService()
