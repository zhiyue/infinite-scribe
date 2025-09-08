"""
Database bootstrap utility

Runs initial schema/migration setup for all data stores used in the
novel genesis stage:

- PostgreSQL: apply Alembic migrations (tables, constraints, indexes)
- Neo4j: create required constraints and indexes
- Milvus: create novel_embeddings_v1 collection (768-dim) and index
- Redis: connectivity + cache TTL sanity (ConversationCacheManager)

Usage (from apps/backend):
  uv run python -m src.db.bootstrap

Or via project script (after pyproject update):
  uv run is-db-bootstrap
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

from src.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BootstrapResult:
    """Result of a bootstrap operation."""

    service_name: str
    success: bool
    error_message: str | None = None

    @property
    def failed(self) -> bool:
        return not self.success


class DatabaseBootstrapper(ABC):
    """Base class for database bootstrap operations."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def bootstrap(self) -> BootstrapResult:
        """Execute bootstrap operation with standardized error handling."""
        try:
            await self._execute_bootstrap()
            self.logger.info(f"{self.service_name} bootstrap completed successfully")
            return BootstrapResult(self.service_name, success=True)
        except ImportError as e:
            # Handle optional dependencies gracefully
            if self._is_optional_dependency():
                self.logger.warning(f"{self.service_name} dependencies not available; skipping bootstrap")
                return BootstrapResult(self.service_name, success=True, error_message=str(e))
            self.logger.error(f"{self.service_name} bootstrap failed due to missing dependency: {e}")
            return BootstrapResult(self.service_name, success=False, error_message=str(e))
        except Exception as e:
            self.logger.error(f"{self.service_name} bootstrap failed: {e}")
            return BootstrapResult(self.service_name, success=False, error_message=str(e))

    @abstractmethod
    async def _execute_bootstrap(self) -> None:
        """Execute the actual bootstrap logic."""
        pass

    def _is_optional_dependency(self) -> bool:
        """Override for services with optional dependencies."""
        return False


class PostgreSQLBootstrapper(DatabaseBootstrapper):
    """Handles PostgreSQL Alembic migrations."""

    def __init__(self):
        super().__init__("PostgreSQL")

    async def _execute_bootstrap(self) -> None:
        """Apply Alembic migrations to head."""
        alembic_ini_path = self._get_alembic_ini_path()
        if not alembic_ini_path.exists():
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")

        cfg = AlembicConfig(str(alembic_ini_path))
        self.logger.info("Applying Alembic migrations to head...")
        alembic_command.upgrade(cfg, "head")

    def _get_alembic_ini_path(self) -> Path:
        """Get path to alembic.ini configuration file."""
        # Locate alembic.ini relative to this file: apps/backend/alembic.ini
        backend_root = Path(__file__).resolve().parents[2]
        return backend_root / "alembic.ini"


class Neo4jBootstrapper(DatabaseBootstrapper):
    """Handles Neo4j schema initialization."""

    def __init__(self):
        super().__init__("Neo4j")

    async def _execute_bootstrap(self) -> None:
        """Create Neo4j constraints and indexes (idempotent)."""
        from src.db.graph.schema import Neo4jSchemaManager
        from src.db.graph.session import create_neo4j_session

        async with create_neo4j_session() as session:
            schema = Neo4jSchemaManager(session)
            await schema.initialize_schema()

            is_verified = await schema.verify_schema()
            if not is_verified:
                raise RuntimeError("Neo4j schema verification failed")


class MilvusBootstrapper(DatabaseBootstrapper):
    """Handles Milvus collection and index creation."""

    def __init__(self):
        super().__init__("Milvus")

    async def _execute_bootstrap(self) -> None:
        """Create Milvus collection and index for novel embeddings."""
        from src.db.vector.milvus import MilvusSchemaManager

        schema = MilvusSchemaManager(host=settings.milvus_host, port=str(settings.milvus_port))
        try:
            is_initialized = await schema.initialize_novel_embeddings()
            if not is_initialized:
                raise RuntimeError("Milvus novel embeddings initialization failed")
        finally:
            await schema.disconnect()

    def _is_optional_dependency(self) -> bool:
        """Milvus has optional dependencies."""
        return True


class RedisBootstrapper(DatabaseBootstrapper):
    """Handles Redis connectivity and cache configuration validation."""

    EXPECTED_SESSION_TTL = 30 * 24 * 60 * 60  # 30 days in seconds

    def __init__(self):
        super().__init__("Redis")

    async def _execute_bootstrap(self) -> None:
        """Check Redis connectivity and cache TTL defaults."""
        from src.common.services.conversation_cache import ConversationCacheManager

        cache = ConversationCacheManager()
        try:
            is_connected = await cache.connect()
            if not is_connected:
                raise ConnectionError("Failed to connect to Redis for ConversationCacheManager")

            self._validate_cache_configuration(cache)
        finally:
            await cache.disconnect()

    def _validate_cache_configuration(self, cache: Any) -> None:
        """Validate cache TTL configuration."""
        if cache.default_session_ttl != self.EXPECTED_SESSION_TTL:
            raise ValueError(
                f"Invalid cache TTL configuration: expected {self.EXPECTED_SESSION_TTL}, "
                f"got {cache.default_session_ttl}"
            )


class BootstrapOrchestrator:
    """Orchestrates the bootstrap process for all database services."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.orchestrator")
        self.bootstrappers = [
            PostgreSQLBootstrapper(),
            Neo4jBootstrapper(),
            MilvusBootstrapper(),
            RedisBootstrapper(),
        ]

    async def bootstrap_all(self) -> int:
        """Run all bootstrap steps sequentially."""
        self.logger.info("Starting database bootstrap...")

        results = await self._execute_bootstrap_steps()
        return self._process_results(results)

    async def _execute_bootstrap_steps(self) -> list[BootstrapResult]:
        """Execute all bootstrap steps and collect results."""
        results = []
        for bootstrapper in self.bootstrappers:
            result = await bootstrapper.bootstrap()
            results.append(result)
        return results

    def _process_results(self, results: list[BootstrapResult]) -> int:
        """Process bootstrap results and return appropriate exit code."""
        failed_services = [r.service_name for r in results if r.failed]

        if failed_services:
            self.logger.error(f"Bootstrap completed with failures: {failed_services}")
            return 1

        self.logger.info("All data stores bootstrapped successfully")
        return 0


async def bootstrap_all() -> int:
    """Run all bootstrap steps sequentially."""
    orchestrator = BootstrapOrchestrator()
    return await orchestrator.bootstrap_all()


def main() -> None:
    """Main entry point for database bootstrap."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    exit_code = asyncio.run(bootstrap_all())
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
