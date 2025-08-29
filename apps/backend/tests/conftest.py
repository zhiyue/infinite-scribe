"""Pytest configuration and shared fixtures."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.api.main import app
from src.database import get_db
from src.models.base import Base

# Configure remote Docker host if requested
if os.environ.get("USE_REMOTE_DOCKER", "false").lower() == "true":
    remote_docker_host = os.environ.get("REMOTE_DOCKER_HOST", "tcp://192.168.2.202:2375")
    os.environ["DOCKER_HOST"] = remote_docker_host
    # Only disable Ryuk if explicitly requested
    if os.environ.get("DISABLE_RYUK", "false").lower() == "true":
        os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@asynccontextmanager
async def create_async_context_mock(return_value):
    """创建异步上下文管理器 Mock 的工厂函数.

    使用 contextlib.asynccontextmanager 装饰器创建异步上下文管理器，
    比自定义类更简洁且符合 Python 惯用法。

    Args:
        return_value: 上下文管理器应该返回的值

    Yields:
        return_value: 传入的值

    Example:
        # Neo4j 测试
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # PostgreSQL 测试
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)
    """
    yield return_value


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Markers for different test types
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring external services")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")


# Service configuration fixtures
@pytest.fixture(scope="session")
def use_external_services():
    """Check if we should use external services instead of testcontainers.

    This fixture determines whether to use:
    - External services at 192.168.2.201 (when USE_EXTERNAL_SERVICES=true)
    - Testcontainers with local or remote Docker (when USE_EXTERNAL_SERVICES=false)

    When using testcontainers, you can additionally set:
    - USE_REMOTE_DOCKER=true to use remote Docker host
    - REMOTE_DOCKER_HOST=tcp://192.168.2.202:2375 (or other host)
    - DISABLE_RYUK=true to disable Ryuk if needed (not recommended)
    """
    return os.environ.get("USE_EXTERNAL_SERVICES", "false").lower() == "true"


@pytest.fixture(scope="session")
def postgres_service(use_external_services):
    """Provide PostgreSQL connection configuration."""
    if use_external_services:
        # Use external service configuration from environment
        yield {
            "host": os.environ.get("POSTGRES_HOST", "localhost"),
            "port": int(os.environ.get("POSTGRES_PORT", "5432")),
            "user": os.environ.get("POSTGRES_USER", "postgres"),
            "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "database": os.environ.get("POSTGRES_DB", "test_db"),
        }
    else:
        # Use testcontainers for local or remote Docker
        from testcontainers.postgres import PostgresContainer

        postgres = None
        try:
            postgres = PostgresContainer("postgres:16")
            postgres.start()
            yield {
                "host": postgres.get_container_host_ip(),
                "port": postgres.get_exposed_port(5432),
                "user": postgres.username,
                "password": postgres.password,
                "database": postgres.dbname,
            }
        finally:
            # Ensure cleanup even if Ryuk fails
            if postgres:
                try:
                    postgres.stop()
                except Exception as e:
                    print(f"Warning: Failed to stop PostgreSQL container: {e}")


@pytest.fixture(scope="session")
def neo4j_service(use_external_services):
    """Provide Neo4j connection configuration."""
    if use_external_services:
        # Use external service configuration from environment
        yield {
            "host": os.environ.get("NEO4J_HOST", "localhost"),
            "port": int(os.environ.get("NEO4J_PORT", "7687")),
            "user": os.environ.get("NEO4J_USER", "neo4j"),
            "password": os.environ.get("NEO4J_PASSWORD", "neo4jtest"),
        }
    else:
        # Use testcontainers for local or remote Docker
        from testcontainers.neo4j import Neo4jContainer

        neo4j = None
        try:
            neo4j = Neo4jContainer("neo4j:5")
            neo4j.start()
            yield {
                "host": neo4j.get_container_host_ip(),
                "port": neo4j.get_exposed_port(7687),
                "user": "neo4j",
                "password": neo4j.password,
            }
        finally:
            # Ensure cleanup even if Ryuk fails
            if neo4j:
                try:
                    neo4j.stop()
                except Exception as e:
                    print(f"Warning: Failed to stop Neo4j container: {e}")


@pytest.fixture(scope="session")
def redis_service(use_external_services):
    """Provide Redis connection configuration."""
    if use_external_services:
        # Use external service configuration from environment
        yield {
            "host": os.environ.get("REDIS_HOST", "localhost"),
            "port": int(os.environ.get("REDIS_PORT", "6379")),
            "password": os.environ.get("REDIS_PASSWORD", ""),
        }
    else:
        # Use testcontainers for local or remote Docker
        from testcontainers.redis import RedisContainer

        redis = None
        try:
            redis = RedisContainer("redis:7-alpine")
            redis.start()
            yield {
                "host": redis.get_container_host_ip(),
                "port": redis.get_exposed_port(6379),
                "password": "",
            }
        finally:
            # Ensure cleanup even if Ryuk fails
            if redis:
                try:
                    redis.stop()
                except Exception as e:
                    print(f"Warning: Failed to stop Redis container: {e}")


# Test database URL - using SQLite in memory for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="session")
async def postgres_test_engine(postgres_service):
    """Create PostgreSQL test database engine for integration tests."""
    # 构建 PostgreSQL URL
    db_url = (
        f"postgresql+asyncpg://{postgres_service['user']}:{postgres_service['password']}"
        f"@{postgres_service['host']}:{postgres_service['port']}/{postgres_service['database']}"
    )
    engine = create_async_engine(db_url)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def postgres_test_session(postgres_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create PostgreSQL test database session for integration tests."""
    async_session = sessionmaker(
        postgres_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def client(test_session):
    """Create test client."""

    def override_get_db():
        return test_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_session):
    """Create async test client."""

    def override_get_db():
        return test_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
async def postgres_async_client(postgres_test_session):
    """Create async test client with PostgreSQL for integration tests."""
    from unittest.mock import AsyncMock, patch

    from tests.unit.test_mocks import mock_email_service, mock_redis

    def override_get_db():
        return postgres_test_session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis),
        patch("src.common.services.email_tasks.email_tasks._send_email_with_retry", new=AsyncMock(return_value=True)),
        patch("src.common.services.email_service.EmailService") as mock_email_cls,
    ):
        mock_email_cls.return_value = mock_email_service
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    # Cleanup
    app.dependency_overrides.clear()
    mock_redis.clear()
    mock_email_service.clear()


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    # Set test environment
    os.environ["NODE_ENV"] = "test"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    # Set required API keys for testing (fake values)
    os.environ["SECRET_KEY"] = "test_secret_key_at_least_32_characters_long"
    os.environ["REDIS_URL"] = "redis://fake:6379/0"  # Will be mocked
    os.environ["FRONTEND_URL"] = "http://localhost:3000"

    # Email settings for testing
    os.environ["EMAIL_FROM"] = "test@example.com"
    os.environ["EMAIL_FROM_NAME"] = "Test App"
    os.environ["RESEND_API_KEY"] = "fake_resend_key"

    yield

    # Cleanup - remove test environment variables
    test_env_vars = [
        "NODE_ENV",
        "DATABASE_URL",
        "SECRET_KEY",
        "REDIS_URL",
        "FRONTEND_URL",
        "EMAIL_FROM",
        "EMAIL_FROM_NAME",
        "RESEND_API_KEY",
    ]
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
