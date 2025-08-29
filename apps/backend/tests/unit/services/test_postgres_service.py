"""Unit tests for PostgreSQL service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.common.services.postgres_service import PostgreSQLService, postgres_service
from tests.conftest import create_async_context_mock


class TestPostgreSQLService:
    """Test cases for PostgreSQL service."""

    @pytest.fixture
    def service(self):
        """Create a new PostgreSQL service instance for each test."""
        return PostgreSQLService()

    def test_init(self, service):
        """Test service initialization."""
        assert service._pool is None
        assert service._lock is not None
        assert isinstance(service._lock, asyncio.Lock)

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.asyncpg.create_pool")
    @patch("src.common.services.postgres_service.settings")
    async def test_connect_success(self, mock_settings, mock_create_pool, service):
        """Test successful connection pool creation."""
        # Setup
        mock_pool = AsyncMock()

        async def mock_create_pool_func(*args, **kwargs):
            return mock_pool

        mock_create_pool.side_effect = mock_create_pool_func
        mock_settings.database.postgres_url = "postgresql+asyncpg://user:pass@host:5432/db"

        # Execute
        await service.connect()

        # Verify
        assert service._pool == mock_pool
        mock_create_pool.assert_called_once_with(
            "postgresql://user:pass@host:5432/db",  # +asyncpg removed
            min_size=5,
            max_size=20,
            command_timeout=60,
            max_inactive_connection_lifetime=300,
        )

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, service):
        """Test connect when already connected."""
        # Setup - simulate already connected
        existing_pool = AsyncMock()
        service._pool = existing_pool

        # Execute
        await service.connect()

        # Verify - should not create new pool
        assert service._pool == existing_pool

    @pytest.mark.asyncio
    @patch("src.common.services.postgres_service.asyncpg.create_pool")
    @patch("src.common.services.postgres_service.settings")
    async def test_connect_failure(self, mock_settings, mock_create_pool, service):
        """Test connection failure."""

        # Setup
        async def mock_create_pool_func(*args, **kwargs):
            raise Exception("Connection failed")

        mock_create_pool.side_effect = mock_create_pool_func
        mock_settings.database.postgres_url = "postgresql+asyncpg://user:pass@host:5432/db"

        # Execute & Verify
        with pytest.raises(Exception, match="Connection failed"):
            await service.connect()

        assert service._pool is None

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self, service):
        """Test disconnection when connected."""
        # Setup
        mock_pool = AsyncMock()
        service._pool = mock_pool

        # Execute
        await service.disconnect()

        # Verify
        mock_pool.close.assert_called_once()
        assert service._pool is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, service):
        """Test disconnection when not connected."""
        # Setup
        service._pool = None

        # Execute
        await service.disconnect()

        # Verify - should not raise any errors
        assert service._pool is None

    @pytest.mark.asyncio
    async def test_check_connection_no_pool(self, service):
        """Test connection check when no pool exists."""
        # Setup
        service._pool = None

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_success(self, service):
        """Test successful connection check."""
        # Setup
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock the acquire method to return an actual context manager instance
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)

        # Mock the async fetchval method
        mock_conn.fetchval = AsyncMock(return_value=1)

        service._pool = mock_pool

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is True
        mock_conn.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_check_connection_wrong_result(self, service):
        """Test connection check when wrong result returned."""
        # Setup
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock the acquire method to return an actual context manager instance
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)

        # Mock the async fetchval method
        mock_conn.fetchval = AsyncMock(return_value=2)  # Wrong value

        service._pool = mock_pool

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_exception(self, service):
        """Test connection check when exception occurs."""
        # Setup
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock the acquire method to return an actual context manager instance
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)

        # Mock the async fetchval method to raise exception
        mock_conn.fetchval = AsyncMock(side_effect=Exception("Query failed"))

        service._pool = mock_pool

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "connect")
    async def test_acquire_calls_connect_when_no_pool(self, mock_connect, service):
        """Test acquire calls connect when no pool exists."""
        # Setup
        service._pool = None
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        async def mock_connect_side_effect():
            service._pool = mock_pool

        mock_connect.side_effect = mock_connect_side_effect

        # Mock the acquire method to return an actual context manager instance
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)

        # Execute
        async with service.acquire() as conn:
            assert conn == mock_conn

        # Verify
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_with_existing_pool(self, service):
        """Test acquire with existing pool."""
        # Setup
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        # Mock the acquire method to return an actual context manager instance
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)

        service._pool = mock_pool

        # Execute
        async with service.acquire() as conn:
            assert conn == mock_conn

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    async def test_verify_schema_success(self, mock_acquire, service):
        """Test successful schema verification."""
        # Setup
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn

        # Mock all required tables exist
        mock_rows = [
            {"tablename": "novels"},
            {"tablename": "chapters"},
            {"tablename": "characters"},
            {"tablename": "worldview_entries"},
            {"tablename": "reviews"},
            {"tablename": "story_arcs"},
        ]
        mock_conn.fetch.return_value = mock_rows

        # Execute
        result = await service.verify_schema()

        # Verify
        assert result is True
        mock_conn.fetch.assert_called_once()

        # Check the SQL query and parameters
        args, kwargs = mock_conn.fetch.call_args
        assert "tablename" in args[0]
        assert "pg_tables" in args[0]
        expected_tables = ["novels", "chapters", "characters", "worldview_entries", "reviews", "story_arcs"]
        assert args[1] == expected_tables

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    async def test_verify_schema_missing_tables(self, mock_acquire, service):
        """Test schema verification with missing tables."""
        # Setup
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn

        # Mock only some tables exist
        mock_rows = [
            {"tablename": "novels"},
            {"tablename": "chapters"},
            # Missing: characters, worldview_entries, reviews, story_arcs
        ]
        mock_conn.fetch.return_value = mock_rows

        # Execute
        result = await service.verify_schema()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    async def test_verify_schema_exception(self, mock_acquire, service):
        """Test schema verification when exception occurs."""
        # Setup
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.side_effect = Exception("Query failed")

        # Execute
        result = await service.verify_schema()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "connect")
    @patch.object(PostgreSQLService, "acquire")
    async def test_execute_calls_connect_when_no_pool(self, mock_acquire, mock_connect, service):
        """Test execute calls connect when no pool exists."""
        # Setup
        service._pool = None
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        # Execute
        result = await service.execute("SELECT 1")

        # Verify
        mock_connect.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    @patch.object(PostgreSQLService, "connect")
    async def test_execute_without_parameters(self, mock_connect, mock_acquire, service):
        """Test execute without parameters."""
        # Setup - simulate already connected state
        service._pool = MagicMock()  # Mock pool to avoid connect() call
        
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn

        # Mock fetch result
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda k: {"id": 1, "name": "test"}[k]
        mock_row.keys.return_value = ["id", "name"]

        # Make the row work with dict()
        mock_row.__iter__ = lambda: iter([("id", 1), ("name", "test")])

        mock_conn.fetch.return_value = [mock_row]

        # Execute
        result = await service.execute("SELECT id, name FROM users")

        # Verify
        mock_conn.fetch.assert_called_once_with("SELECT id, name FROM users")
        assert len(result) == 1
        mock_connect.assert_not_called()  # Should not call connect since pool exists

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    @patch.object(PostgreSQLService, "connect")
    async def test_execute_with_parameters(self, mock_connect, mock_acquire, service):
        """Test execute with parameters."""
        # Setup - simulate already connected state
        service._pool = MagicMock()  # Mock pool to avoid connect() call
        
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn

        # Mock fetch result
        mock_row = MagicMock()
        mock_row.__iter__ = lambda: iter([("id", 1), ("name", "test")])
        mock_conn.fetch.return_value = [mock_row]

        parameters = (1, "test")

        # Execute
        result = await service.execute("SELECT * FROM users WHERE id = $1 AND name = $2", parameters)

        # Verify
        mock_conn.fetch.assert_called_once_with("SELECT * FROM users WHERE id = $1 AND name = $2", 1, "test")
        assert len(result) == 1
        mock_connect.assert_not_called()  # Should not call connect since pool exists

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    @patch.object(PostgreSQLService, "connect")
    async def test_execute_with_list_parameters(self, mock_connect, mock_acquire, service):
        """Test execute with list parameters."""
        # Setup - simulate already connected state
        service._pool = MagicMock()  # Mock pool to avoid connect() call
        
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        parameters = [1, "test"]

        # Execute
        result = await service.execute("SELECT * FROM users WHERE id = $1 AND name = $2", parameters)

        # Verify
        mock_conn.fetch.assert_called_once_with("SELECT * FROM users WHERE id = $1 AND name = $2", 1, "test")
        assert result == []
        mock_connect.assert_not_called()  # Should not call connect since pool exists

    @pytest.mark.asyncio
    @patch.object(PostgreSQLService, "acquire")
    @patch.object(PostgreSQLService, "connect")
    async def test_execute_empty_result(self, mock_connect, mock_acquire, service):
        """Test execute with empty result."""
        # Setup - simulate already connected state
        service._pool = MagicMock()  # Mock pool to avoid connect() call
        
        mock_conn = AsyncMock()
        mock_acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetch.return_value = []

        # Execute
        result = await service.execute("SELECT * FROM users WHERE id = -1")

        # Verify
        mock_conn.fetch.assert_called_once_with("SELECT * FROM users WHERE id = -1")
        assert result == []
        mock_connect.assert_not_called()  # Should not call connect since pool exists

    def test_module_instance_available(self):
        """Test that the module-level instance is available."""
        assert postgres_service is not None
        assert isinstance(postgres_service, PostgreSQLService)
