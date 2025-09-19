"""Neo4j database connection service."""

import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from src.core.config import settings

logger = logging.getLogger(__name__)


# Neo4j database connection service.
class Neo4jService:
    """Manages Neo4j database connections."""

    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Initialize Neo4j driver."""
        if self._driver is not None:
            return

        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.database.neo4j_url,
                auth=(settings.database.neo4j_user, settings.database.neo4j_password),
                max_connection_lifetime=300,
                max_connection_pool_size=50,
                connection_timeout=30.0,
            )
            logger.info("Neo4j driver created successfully")
        except Exception as e:
            logger.error(f"Failed to create Neo4j driver: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Neo4j driver."""
        if self._driver is None:
            return

        await self._driver.close()
        self._driver = None
        logger.info("Neo4j driver closed")

    async def check_connection(self) -> bool:
        """Check if database is accessible."""
        if self._driver is None:
            return False

        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS value")
                record = await result.single()
                return record is not None and record["value"] == 1
        except Exception as e:
            logger.error(f"Neo4j connection check failed: {e}")
            return False

    async def verify_constraints(self) -> bool:
        """Verify required constraints exist."""
        if self._driver is None:
            await self.connect()

        if self._driver is None:
            return False

        try:
            async with self._driver.session() as session:
                result = await session.run("SHOW CONSTRAINTS")
                constraints = await result.data()

                # Check for novel_id uniqueness constraint
                has_novel_constraint = any(
                    c.get("labelsOrTypes") == ["Novel"] and c.get("properties") == ["novel_id"] for c in constraints
                )

                if not has_novel_constraint:
                    logger.warning("Missing Novel(novel_id) uniqueness constraint")
                    return False

                logger.info("All required Neo4j constraints exist")
                return True
        except Exception as e:
            logger.error(f"Constraint verification failed: {e}")
            return False

    async def execute(self, query: str, parameters: dict | None = None):
        """Execute a Cypher query."""
        if self._driver is None:
            await self.connect()

        if self._driver is None:
            raise RuntimeError("Failed to establish Neo4j connection")

        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})  # pyright: ignore[reportArgumentType]
            return await result.data()


neo4j_service = Neo4jService()
