"""Unit tests for Redis service."""

from unittest.mock import AsyncMock, patch

import pytest
from src.common.services.redis_service import RedisService


class TestRedisService:
    """Test cases for RedisService."""

    @pytest.fixture
    def redis_service(self):
        """Create Redis service instance."""
        return RedisService()

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = AsyncMock()
        return client

    @pytest.mark.asyncio
    @patch("src.common.services.redis_service.redis.from_url")
    async def test_connect(self, mock_from_url, redis_service):
        """Test Redis connection establishment."""
        # Arrange
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        # Act
        await redis_service.connect()

        # Assert
        assert redis_service._client == mock_client
        mock_from_url.assert_called_once()

        # Test that it doesn't reconnect if already connected
        await redis_service.connect()
        mock_from_url.assert_called_once()  # Still only called once

    @pytest.mark.asyncio
    async def test_disconnect(self, redis_service, mock_redis_client):
        """Test Redis disconnection."""
        # Arrange
        redis_service._client = mock_redis_client

        # Act
        await redis_service.disconnect()

        # Assert
        assert redis_service._client is None
        mock_redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_no_client(self, redis_service):
        """Test disconnect when no client exists."""
        # Act & Assert - Should not raise error
        await redis_service.disconnect()
        assert redis_service._client is None

    @pytest.mark.asyncio
    async def test_check_connection_success(self, redis_service, mock_redis_client):
        """Test successful connection check."""
        # Arrange
        redis_service._client = mock_redis_client
        mock_redis_client.ping.return_value = "PONG"

        # Act
        result = await redis_service.check_connection()

        # Assert
        assert result is True
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_no_client(self, redis_service):
        """Test connection check when no client exists."""
        # Act
        result = await redis_service.check_connection()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, redis_service, mock_redis_client):
        """Test connection check when ping fails."""
        # Arrange
        redis_service._client = mock_redis_client
        mock_redis_client.ping.side_effect = Exception("Connection failed")

        # Act
        result = await redis_service.check_connection()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_success(self, redis_service, mock_redis_client):
        """Test successful get operation."""
        # Arrange
        redis_service._client = mock_redis_client
        mock_redis_client.get.return_value = "test_value"

        # Act
        result = await redis_service.get("test_key")

        # Assert
        assert result == "test_value"
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_no_client(self, redis_service):
        """Test get operation without client."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await redis_service.get("test_key")

    @pytest.mark.asyncio
    async def test_set_success(self, redis_service, mock_redis_client):
        """Test successful set operation."""
        # Arrange
        redis_service._client = mock_redis_client

        # Act
        await redis_service.set("test_key", "test_value", expire=60)

        # Assert
        mock_redis_client.set.assert_called_once_with("test_key", "test_value", ex=60)

    @pytest.mark.asyncio
    async def test_set_no_expire(self, redis_service, mock_redis_client):
        """Test set operation without expiration."""
        # Arrange
        redis_service._client = mock_redis_client

        # Act
        await redis_service.set("test_key", "test_value")

        # Assert
        mock_redis_client.set.assert_called_once_with("test_key", "test_value", ex=None)

    @pytest.mark.asyncio
    async def test_set_no_client(self, redis_service):
        """Test set operation without client."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await redis_service.set("test_key", "test_value")

    @pytest.mark.asyncio
    async def test_delete_success(self, redis_service, mock_redis_client):
        """Test successful delete operation."""
        # Arrange
        redis_service._client = mock_redis_client

        # Act
        await redis_service.delete("test_key")

        # Assert
        mock_redis_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_no_client(self, redis_service):
        """Test delete operation without client."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await redis_service.delete("test_key")

    @pytest.mark.asyncio
    async def test_exists_true(self, redis_service, mock_redis_client):
        """Test exists operation when key exists."""
        # Arrange
        redis_service._client = mock_redis_client
        mock_redis_client.exists.return_value = 1

        # Act
        result = await redis_service.exists("test_key")

        # Assert
        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_false(self, redis_service, mock_redis_client):
        """Test exists operation when key doesn't exist."""
        # Arrange
        redis_service._client = mock_redis_client
        mock_redis_client.exists.return_value = 0

        # Act
        result = await redis_service.exists("test_key")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_no_client(self, redis_service):
        """Test exists operation without client."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await redis_service.exists("test_key")

    @pytest.mark.asyncio
    @patch("src.common.services.redis_service.redis.from_url")
    async def test_acquire_context_manager_with_existing_client(self, mock_from_url, redis_service):
        """Test acquire context manager with existing client."""
        # Arrange
        mock_client = AsyncMock()
        redis_service._client = mock_client

        # Act
        async with redis_service.acquire() as client:
            # Assert
            assert client == mock_client
            mock_from_url.assert_not_called()  # Should not create new connection

    @pytest.mark.asyncio
    @patch("src.common.services.redis_service.redis.from_url")
    async def test_acquire_context_manager_without_client(self, mock_from_url, redis_service):
        """Test acquire context manager without existing client."""
        # Arrange
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        # Act
        async with redis_service.acquire() as client:
            # Assert
            assert client == mock_client
            assert redis_service._client == mock_client
            mock_from_url.assert_called_once()

        # Client should still be connected after context exit
        assert redis_service._client == mock_client

    @pytest.mark.asyncio
    @patch("src.common.services.redis_service.settings")
    @patch("src.common.services.redis_service.redis.from_url")
    async def test_connect_with_settings(self, mock_from_url, mock_settings, redis_service):
        """Test connection uses correct settings."""
        # Arrange
        mock_settings.database.redis_url = "redis://test:6379"
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        # Act
        await redis_service.connect()

        # Assert
        mock_from_url.assert_called_once_with(
            "redis://test:6379",
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
