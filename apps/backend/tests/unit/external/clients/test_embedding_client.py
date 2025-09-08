"""Unit tests for Embedding Client."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from src.external.clients import EmbeddingClient, embedding_service
from src.external.clients.errors import (
    ExternalServiceError,
    ServiceResponseError,
    ServiceValidationError,
)


class TestEmbeddingClient:
    """Test cases for Embedding Client."""

    @pytest.fixture
    def client(self):
        """Create a new embedding client instance for each test."""
        return EmbeddingClient(base_url="http://localhost:11434", model="test-model")

    def test_init(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:11434"
        assert client.model == "test-model"
        assert client._client is None

    @pytest.mark.asyncio
    async def test_check_connection_success(self, client):
        """Test successful connection check."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.get.return_value = mock_response
        client._client = mock_client

        # Execute
        result = await client.check_connection()

        # Verify
        assert result is True
        # Note: BaseHttpClient.get constructs full URL internally
        args, kwargs = mock_client.get.call_args
        assert args[0] == "http://localhost:11434/api/tags"

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, client):
        """Test connection check failure."""
        # Setup
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        client._client = mock_client

        # Execute
        result = await client.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_get_embedding_success_embeddings_format(self, client):
        """Test successful embedding retrieval with 'embeddings' format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        mock_client.post.return_value = mock_response
        client._client = mock_client

        # Execute
        result = await client.get_embedding("test text")

        # Verify
        assert result == [0.1, 0.2, 0.3]
        # Note: BaseHttpClient.post constructs full URL internally
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://localhost:11434/api/embed"
        assert kwargs["json"] == {"model": "test-model", "input": "test text"}
        assert kwargs["headers"] == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    async def test_get_embedding_success_embedding_format(self, client):
        """Test successful embedding retrieval with 'embedding' format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.4, 0.5, 0.6]}

        mock_client.post.return_value = mock_response
        client._client = mock_client

        # Execute
        result = await client.get_embedding("test text")

        # Verify
        assert result == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_get_embedding_empty_text(self, client):
        """Test embedding retrieval with empty text."""
        # Execute & Verify
        with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
            await client.get_embedding("")

    @pytest.mark.asyncio
    async def test_get_embedding_whitespace_only_text(self, client):
        """Test embedding retrieval with whitespace-only text."""
        # Execute & Verify
        with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
            await client.get_embedding("   ")

    @pytest.mark.asyncio
    async def test_get_embedding_empty_embeddings_list(self, client):
        """Test embedding retrieval with empty embeddings list."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": []}

        mock_client.post.return_value = mock_response
        client._client = mock_client

        # Execute & Verify
        # Note: ServiceResponseError is wrapped in ExternalServiceError by handle_connection_error
        with pytest.raises(ExternalServiceError, match="Empty embeddings array"):
            await client.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_unexpected_format(self, client):
        """Test embedding retrieval with unexpected response format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"unknown_field": "value"}

        mock_client.post.return_value = mock_response
        client._client = mock_client

        # Execute & Verify
        # Note: ServiceResponseError is wrapped in ExternalServiceError by handle_connection_error
        with pytest.raises(ExternalServiceError, match="Unexpected response format"):
            await client.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_http_status_error(self, client):
        """Test embedding retrieval with HTTP status error."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        http_error = httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=mock_response)
        mock_client.post.side_effect = http_error
        client._client = mock_client

        # Execute & Verify
        with pytest.raises(ExternalServiceError):
            await client.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_connection_error(self, client):
        """Test embedding retrieval with connection error."""
        # Setup
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        client._client = mock_client

        # Execute & Verify
        with pytest.raises(ExternalServiceError):
            await client.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_success(self, client):
        """Test successful batch embedding retrieval."""
        # Setup
        client.get_embedding = AsyncMock()
        client.get_embedding.side_effect = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        texts = ["text1", "text2", "text3"]

        # Execute
        result = await client.get_embeddings_batch(texts)

        # Verify
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        assert client.get_embedding.call_count == 3
        client.get_embedding.assert_any_call("text1")
        client.get_embedding.assert_any_call("text2")
        client.get_embedding.assert_any_call("text3")

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_empty_list(self, client):
        """Test batch embedding retrieval with empty list raises validation error."""
        # Execute & Verify
        with pytest.raises(ServiceValidationError, match="Texts list cannot be empty"):
            await client.get_embeddings_batch([])

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_partial_failure(self, client):
        """Test batch embedding retrieval with partial failure."""
        # Setup
        client.get_embedding = AsyncMock()
        client.get_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            ServiceValidationError("EmbeddingAPI", "Failed to get embedding"),
        ]

        texts = ["text1", "text2"]

        # Execute & Verify
        with pytest.raises(ServiceValidationError):
            await client.get_embeddings_batch(texts)

        assert client.get_embedding.call_count == 2

    def test_extract_embedding_from_response_embeddings_format(self, client):
        """Test embedding extraction with embeddings format."""
        response_data = {"embeddings": [[0.1, 0.2, 0.3]]}
        result = client._extract_embedding_from_response(response_data)
        assert result == [0.1, 0.2, 0.3]

    def test_extract_embedding_from_response_embedding_format(self, client):
        """Test embedding extraction with embedding format."""
        response_data = {"embedding": [0.4, 0.5, 0.6]}
        result = client._extract_embedding_from_response(response_data)
        assert result == [0.4, 0.5, 0.6]

    def test_extract_embedding_from_response_empty_embeddings(self, client):
        """Test embedding extraction with empty embeddings."""
        response_data = {"embeddings": []}
        with pytest.raises(ServiceResponseError, match="Empty embeddings array"):
            client._extract_embedding_from_response(response_data)

    def test_extract_embedding_from_response_missing_field(self, client):
        """Test embedding extraction with missing field."""
        response_data = {"unknown": "value"}
        with pytest.raises(ServiceResponseError, match="Unexpected response format"):
            client._extract_embedding_from_response(response_data)

    def test_module_instance_available(self):
        """Test that the module-level instance is available."""
        assert embedding_service is not None
        assert isinstance(embedding_service, EmbeddingClient)

    def test_repr(self, client):
        """Test string representation of the client."""
        expected = "EmbeddingClient(base_url='http://localhost:11434', model='test-model')"
        assert repr(client) == expected
