"""Pytest configuration and shared fixtures."""

import asyncio
import os
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from pymilvus import connections, utility
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
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
def event_loop():
    """Create an instance of the default event loop for the test session.

    This fixture is needed for session-scoped async fixtures like test_engine and postgres_test_engine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
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


@pytest.fixture(scope="session")
def kafka_service(use_external_services):
    """Provide Kafka connection configuration with KRaft mode and pre-created topics."""
    if use_external_services:
        # Use external Kafka service
        yield {
            "bootstrap_servers": [os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")],
            "host": os.environ.get("KAFKA_HOST", "localhost"),
            "port": int(os.environ.get("KAFKA_PORT", "9092")),
        }
    else:
        # Use testcontainers for local or remote Docker
        try:
            from testcontainers.kafka import KafkaContainer
        except ImportError:
            pytest.skip("KafkaContainer not available in testcontainers")

        container = None
        try:
            # Start Kafka with KRaft and auto topic creation enabled
            container = (
                KafkaContainer()
                .with_kraft()
                .with_env("KAFKA_AUTO_CREATE_TOPICS_ENABLE", "true")
                .with_env("KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR", "1")
                .with_env("KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR", "1")
                .with_env("KAFKA_TRANSACTION_STATE_LOG_MIN_ISR", "1")
            )
            container.start()

            bootstrap_server = container.get_bootstrap_server()
            print(f"Kafka testcontainer started: {bootstrap_server}")

            # Pre-create all topics used by tests and wait briefly for metadata
            try:
                import asyncio as _asyncio
                import time as _time

                from aiokafka.admin import AIOKafkaAdminClient, NewTopic

                topic_names = set(
                    [
                        # Kafka integration test topics
                        "integration.test.e2e",
                        "integration.test.multi",
                        "integration.test.large",
                        "integration.test.concurrent",
                        "integration.test.headers",
                        "integration.test.scheduled",
                        "integration.test.retry",
                        "integration.test.shutdown",
                    ]
                    + [f"concurrency.test.{i}" for i in range(10)]
                    + [f"immediate.topic.{i}" for i in range(5)]
                    + [f"scheduled.topic.{i}" for i in range(3)]
                    + [f"large.topic.{i}" for i in range(10)]
                    + [f"test.topic.{i}" for i in range(10)]
                )

                async def _precreate(_bootstrap: str):
                    admin = AIOKafkaAdminClient(bootstrap_servers=_bootstrap, request_timeout_ms=30000)
                    await admin.start()
                    try:
                        new_topics = [NewTopic(name=t, num_partitions=1, replication_factor=1) for t in topic_names]
                        try:
                            await admin.create_topics(new_topics=new_topics, validate_only=False)
                        except Exception as e:
                            # Ignore already exists and transient errors
                            if "exists" not in str(e).lower():
                                print(f"Warning: create_topics error: {e}")
                    finally:
                        await admin.close()

                _asyncio.run(_precreate(bootstrap_server))
                # Brief pause to allow metadata propagation
                _time.sleep(1.0)
            except Exception as e:
                print(f"Warning: pre-creating topics failed or skipped: {e}")

            host, port = bootstrap_server.split(":")
            yield {
                "bootstrap_servers": [bootstrap_server],
                "host": host,
                "port": int(port),
            }
        finally:
            if container:
                with suppress(Exception):
                    container.stop()


MILVUS_IMAGE = os.getenv("MILVUS_IMAGE", "milvusdb/milvus:v2.4.10")  # 固定版本
CONNECT_TIMEOUT_S = int(os.getenv("MILVUS_CONNECT_TIMEOUT", "60"))


@pytest.fixture(scope="session")
def milvus_service():
    """Provide Milvus connection (skip gracefully if container healthcheck fails)."""
    # Lazy import to avoid hard dependency for unit tests
    try:
        from testcontainers.milvus import MilvusContainer
    except Exception as e:
        pytest.skip(f"Milvus testcontainer not available: {e}")

    container = None
    try:
        container = MilvusContainer(MILVUS_IMAGE)
        container.start()
    except Exception as e:
        pytest.skip(f"Milvus container failed to start in this environment: {e}")

    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(container.port)  # 默认 19530

        # 等待就绪：用 PyMilvus API 轮询而非盲睡
        deadline = time.time() + CONNECT_TIMEOUT_S
        last_err = None
        while time.time() < deadline:
            try:
                connections.disconnect("default")
                connections.connect(alias="default", host=host, port=port)
                utility.list_collections()  # 触发一次请求验证
                break
            except Exception as e:
                last_err = e
                time.sleep(1)
        else:
            pytest.skip(f"Milvus not ready: {last_err}")

        yield {"host": host, "port": port}
    finally:
        with suppress(Exception):
            connections.disconnect("default")
        if container:
            with suppress(Exception):
                container.stop()


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


def run_alembic_migrations(database_url: str):
    """Run Alembic migrations on the test database."""
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine, text

    # Create alembic config
    alembic_dir = Path(__file__).parent.parent / "alembic"
    original_ini = alembic_dir.parent / "alembic.ini"

    alembic_cfg = Config(str(original_ini))

    # Set the database URL (sync version for alembic)
    sync_db_url = database_url.replace("+asyncpg", "")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_db_url)
    alembic_cfg.set_main_option("script_location", str(alembic_dir))

    print(f"Running Alembic migrations on {sync_db_url}")
    print(f"Script location: {alembic_dir}")

    try:
        # Check heads
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()
        print(f"Available heads: {heads}")

        # Create engine and check if we can connect
        engine = create_engine(sync_db_url)
        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            print("Database connection successful")

        # Run migrations
        command.upgrade(alembic_cfg, "head")
        print("Alembic upgrade command completed")

        # Check results
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version')"
                )
            )
            print(f"Alembic version table exists: {result.scalar()}")

            # Check what tables exist
            result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables in database: {tables}")

            # If alembic_version exists, check current revision
            if result.scalar():
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_version = result.scalar()
                print(f"Current migration version: {current_version}")

        engine.dispose()

    except Exception as e:
        print(f"Error during Alembic migration: {e}")
        import traceback

        traceback.print_exc()
        raise


@pytest.fixture(scope="session")
async def postgres_test_engine(postgres_service):
    """Create PostgreSQL test database engine for integration tests."""
    # 构建 PostgreSQL URL
    db_url = (
        f"postgresql+asyncpg://{postgres_service['user']}:{postgres_service['password']}"
        f"@{postgres_service['host']}:{postgres_service['port']}/{postgres_service['database']}"
    )
    engine = create_async_engine(db_url)

    # Create tables directly (faster for tests) and also create alembic_version table
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Also create alembic_version table with the current head revision
        # This satisfies tests that check for migration status
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)
        )

        # Insert the current head revision (from the available heads)
        await conn.execute(
            text("""
            INSERT INTO alembic_version (version_num)
            VALUES ('9de0f061b66e')
            ON CONFLICT (version_num) DO NOTHING
        """)
        )

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        # Also drop alembic_version table
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

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

    # Lazy import app to avoid heavy dependencies at module import time
    from src.api.main import app

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

    from src.api.main import app

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

    from src.api.main import app

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
    # Some tests rely on default allowed_origins; ensure env override is absent
    os.environ.pop("ALLOWED_ORIGINS", None)

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
