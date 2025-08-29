"""Unit tests for Neo4j service."""

from unittest.mock import AsyncMock, patch

import pytest
from src.common.services.neo4j_service import Neo4jService, neo4j_service
from tests.conftest import create_async_context_mock


class TestNeo4jService:
    """Test cases for Neo4j service."""

    @pytest.fixture
    def service(self):
        """Create a new Neo4j service instance for each test."""
        return Neo4jService()

    def test_init(self, service):
        """Test service initialization."""
        assert service._driver is None

    @pytest.mark.asyncio
    @patch("src.common.services.neo4j_service.AsyncGraphDatabase.driver")
    @patch("src.common.services.neo4j_service.settings")
    async def test_connect_success(self, mock_settings, mock_driver_factory, service):
        """Test successful connection to Neo4j."""
        # Setup
        mock_driver = AsyncMock()
        mock_driver_factory.return_value = mock_driver
        mock_settings.database.neo4j_url = "bolt://localhost:7687"
        mock_settings.database.neo4j_user = "neo4j"
        mock_settings.database.neo4j_password = "password"

        # Execute
        await service.connect()

        # Verify
        assert service._driver == mock_driver
        mock_driver_factory.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password"),
            max_connection_lifetime=300,
            max_connection_pool_size=50,
            connection_timeout=30.0,
        )

    @pytest.mark.asyncio
    @patch("src.common.services.neo4j_service.AsyncGraphDatabase.driver")
    async def test_connect_already_connected(self, mock_driver_factory, service):
        """Test connect when already connected."""
        # Setup - simulate already connected
        existing_driver = AsyncMock()
        service._driver = existing_driver

        # Execute
        await service.connect()

        # Verify - should not create new driver
        mock_driver_factory.assert_not_called()
        assert service._driver == existing_driver

    @pytest.mark.asyncio
    @patch("src.common.services.neo4j_service.AsyncGraphDatabase.driver")
    @patch("src.common.services.neo4j_service.settings")
    async def test_connect_failure(self, mock_settings, mock_driver_factory, service):
        """Test connection failure."""
        # Setup
        mock_driver_factory.side_effect = Exception("Connection failed")
        mock_settings.database.neo4j_url = "bolt://localhost:7687"
        mock_settings.database.neo4j_user = "neo4j"
        mock_settings.database.neo4j_password = "password"

        # Execute & Verify
        with pytest.raises(Exception, match="Connection failed"):
            await service.connect()

        assert service._driver is None

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self, service):
        """Test disconnection when connected."""
        # Setup
        mock_driver = AsyncMock()
        service._driver = mock_driver

        # Execute
        await service.disconnect()

        # Verify
        mock_driver.close.assert_called_once()
        assert service._driver is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, service):
        """Test disconnection when not connected."""
        # Setup
        service._driver = None

        # Execute
        await service.disconnect()

        # Verify - should not raise any errors
        assert service._driver is None

    @pytest.mark.asyncio
    async def test_check_connection_no_driver(self, service):
        """Test connection check when no driver exists."""
        # Setup
        service._driver = None

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_success(self, service):
        """Test successful connection check."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"value": 1}

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.single = AsyncMock(return_value=mock_record)

        service._driver = mock_driver

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is True
        mock_session.run.assert_called_once_with("RETURN 1 AS value")
        mock_result.single.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_no_record(self, service):
        """Test connection check when no record returned."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.single = AsyncMock(return_value=None)

        service._driver = mock_driver

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_wrong_value(self, service):
        """Test connection check when wrong value returned."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"value": 2}  # Wrong value

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.single = AsyncMock(return_value=mock_record)

        service._driver = mock_driver

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_exception(self, service):
        """Test connection check when exception occurs."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async method to raise exception
        mock_session.run = AsyncMock(side_effect=Exception("Query failed"))

        service._driver = mock_driver

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch.object(Neo4jService, "connect")
    async def test_verify_constraints_no_driver_calls_connect(self, mock_connect, service):
        """Test constraint verification calls connect when no driver."""
        # Setup
        service._driver = None
        mock_connect.return_value = None

        # After connect, still no driver (connection failed)
        # Execute
        result = await service.verify_constraints()

        # Verify
        mock_connect.assert_called_once()
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_constraints_success(self, service):
        """Test successful constraint verification."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock constraints data - includes required constraint
        constraints_data = [
            {"labelsOrTypes": ["Novel"], "properties": ["novel_id"]},
            {"labelsOrTypes": ["User"], "properties": ["email"]},
        ]

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.data = AsyncMock(return_value=constraints_data)

        service._driver = mock_driver

        # Execute
        result = await service.verify_constraints()

        # Verify
        assert result is True
        mock_session.run.assert_called_once_with("SHOW CONSTRAINTS")
        mock_result.data.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_constraints_missing_constraint(self, service):
        """Test constraint verification when required constraint is missing."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock constraints data - missing required constraint
        constraints_data = [
            {"labelsOrTypes": ["User"], "properties": ["email"]},
        ]

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.data = AsyncMock(return_value=constraints_data)

        service._driver = mock_driver

        # Execute
        result = await service.verify_constraints()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_constraints_exception(self, service):
        """Test constraint verification when exception occurs."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async method to raise exception
        mock_session.run = AsyncMock(side_effect=Exception("Query failed"))

        service._driver = mock_driver

        # Execute
        result = await service.verify_constraints()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch.object(Neo4jService, "connect")
    async def test_execute_calls_connect_when_no_driver(self, mock_connect, service):
        """Test execute calls connect when no driver exists."""
        # Setup
        service._driver = None
        mock_connect.return_value = None

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Failed to establish Neo4j connection"):
            await service.execute("RETURN 1")

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_success_without_parameters(self, service):
        """Test successful query execution without parameters."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        expected_data = [{"value": 1}]

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.data = AsyncMock(return_value=expected_data)

        service._driver = mock_driver

        # Execute
        result = await service.execute("RETURN 1 AS value")

        # Verify
        assert result == expected_data
        mock_session.run.assert_called_once_with("RETURN 1 AS value", {})
        mock_result.data.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_success_with_parameters(self, service):
        """Test successful query execution with parameters."""
        # Setup
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        expected_data = [{"name": "test"}]
        parameters = {"name": "test"}

        # Mock the session method to return an actual context manager instance
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # Mock async methods
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_result.data = AsyncMock(return_value=expected_data)

        service._driver = mock_driver

        # Execute
        result = await service.execute("RETURN $name AS name", parameters)

        # Verify
        assert result == expected_data
        mock_session.run.assert_called_once_with("RETURN $name AS name", parameters)
        mock_result.data.assert_called_once()

    def test_module_instance_available(self):
        """Test that the module-level instance is available."""
        assert neo4j_service is not None
        assert isinstance(neo4j_service, Neo4jService)
