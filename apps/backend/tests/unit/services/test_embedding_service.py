"""Unit tests for Embedding service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.common.services.embedding_service import EmbeddingService, embedding_service


class TestEmbeddingService:
    """Test cases for Embedding service."""

    @pytest.fixture
    def service(self):
        """Create a new embedding service instance for each test."""
        return EmbeddingService()

    def test_init(self, service):
        """Test service initialization."""
        assert service._client is None

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.httpx.AsyncClient")
    async def test_connect_creates_client(self, mock_client_class, service):
        """Test connect creates HTTP client."""
        # Setup
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Execute
        await service.connect()

        # Verify
        mock_client_class.assert_called_once_with(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        assert service._client == mock_client

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, service):
        """Test connect when already connected."""
        # Setup - simulate already connected
        existing_client = AsyncMock()
        service._client = existing_client

        # Execute
        await service.connect()

        # Verify - should not create new client
        assert service._client == existing_client

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self, service):
        """Test disconnection when connected."""
        # Setup
        mock_client = AsyncMock()
        service._client = mock_client

        # Execute
        await service.disconnect()

        # Verify
        mock_client.aclose.assert_called_once()
        assert service._client is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, service):
        """Test disconnection when not connected."""
        # Setup
        service._client = None

        # Execute
        await service.disconnect()

        # Verify - should not raise any errors
        assert service._client is None

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    @patch.object(EmbeddingService, "connect")
    async def test_check_connection_success(self, mock_connect, mock_settings, service):
        """Test successful connection check."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.get.return_value = mock_response
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is True
        mock_client.get.assert_called_once_with("http://localhost:11434/api/tags")

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    @patch.object(EmbeddingService, "connect")
    async def test_check_connection_calls_connect(self, mock_connect, mock_settings, service):
        """Test connection check calls connect when no client."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.get.return_value = mock_response
        mock_settings.embedding_api_url = "http://localhost:11434"

        service._client = None

        async def mock_connect_side_effect():
            service._client = mock_client

        mock_connect.side_effect = mock_connect_side_effect

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is True
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    async def test_check_connection_api_error(self, mock_settings, service):
        """Test connection check when API returns error."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client.get.return_value = mock_response
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_exception(self, service):
        """Test connection check when exception occurs."""
        # Setup
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        service._client = mock_client

        # Execute
        result = await service.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    @patch.object(EmbeddingService, "connect")
    async def test_get_embedding_success_embeddings_format(self, mock_connect, mock_settings, service):
        """Test successful embedding retrieval with 'embeddings' format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        mock_client.post.return_value = mock_response
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"
        mock_settings.embedding_api_model = "nomic-embed-text"

        # Execute
        result = await service.get_embedding("test text")

        # Verify
        assert result == [0.1, 0.2, 0.3]
        mock_client.post.assert_called_once_with(
            "http://localhost:11434/api/embed",
            json={"model": "nomic-embed-text", "input": "test text"},
            headers={"Content-Type": "application/json"},
        )

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    async def test_get_embedding_success_embedding_format(self, mock_settings, service):
        """Test successful embedding retrieval with 'embedding' format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.4, 0.5, 0.6]}

        mock_client.post.return_value = mock_response
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"
        mock_settings.embedding_api_model = "nomic-embed-text"

        # Execute
        result = await service.get_embedding("test text")

        # Verify
        assert result == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    async def test_get_embedding_empty_embeddings_list(self, mock_settings, service):
        """Test embedding retrieval with empty embeddings list."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": []}

        mock_client.post.return_value = mock_response
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"
        mock_settings.embedding_api_model = "nomic-embed-text"

        # Execute
        result = await service.get_embedding("test text")

        # Verify
        assert result == []

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    async def test_get_embedding_unexpected_format(self, mock_settings, service):
        """Test embedding retrieval with unexpected response format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"unknown_field": "value"}

        mock_client.post.return_value = mock_response
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Failed to get embedding"):
            await service.get_embedding("test text")

    @pytest.mark.asyncio
    @patch.object(EmbeddingService, "connect")
    async def test_get_embedding_no_client_calls_connect(self, mock_connect, service):
        """Test get_embedding calls connect when no client."""
        # Setup
        service._client = None

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Embedding service client not connected"):
            await service.get_embedding("test text")

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    async def test_get_embedding_http_status_error(self, mock_settings, service):
        """Test embedding retrieval with HTTP status error."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        http_error = httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=mock_response)
        mock_client.post.side_effect = http_error
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Embedding API error: 400"):
            await service.get_embedding("test text")

    @pytest.mark.asyncio
    @patch("src.common.services.embedding_service.settings")
    async def test_get_embedding_general_exception(self, mock_settings, service):
        """Test embedding retrieval with general exception."""
        # Setup
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Network error")
        service._client = mock_client
        mock_settings.embedding_api_url = "http://localhost:11434"

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Failed to get embedding: Network error"):
            await service.get_embedding("test text")

    @pytest.mark.asyncio
    @patch.object(EmbeddingService, "get_embedding")
    async def test_get_embeddings_batch_success(self, mock_get_embedding, service):
        """Test successful batch embedding retrieval."""
        # Setup
        mock_get_embedding.side_effect = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        texts = ["text1", "text2", "text3"]

        # Execute
        result = await service.get_embeddings_batch(texts)

        # Verify
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        assert mock_get_embedding.call_count == 3
        mock_get_embedding.assert_any_call("text1")
        mock_get_embedding.assert_any_call("text2")
        mock_get_embedding.assert_any_call("text3")

    @pytest.mark.asyncio
    @patch.object(EmbeddingService, "get_embedding")
    async def test_get_embeddings_batch_empty_list(self, mock_get_embedding, service):
        """Test batch embedding retrieval with empty list."""
        # Execute
        result = await service.get_embeddings_batch([])

        # Verify
        assert result == []
        mock_get_embedding.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(EmbeddingService, "get_embedding")
    async def test_get_embeddings_batch_partial_failure(self, mock_get_embedding, service):
        """Test batch embedding retrieval with partial failure."""
        # Setup
        mock_get_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            RuntimeError("Failed to get embedding"),
        ]

        texts = ["text1", "text2"]

        # Execute & Verify
        with pytest.raises(RuntimeError, match="Failed to get embedding"):
            await service.get_embeddings_batch(texts)

        assert mock_get_embedding.call_count == 2

    def test_module_instance_available(self):
        """Test that the module-level instance is available."""
        assert embedding_service is not None
        assert isinstance(embedding_service, EmbeddingService)
