"""Unit tests for Ollama Embedding Provider."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from src.external.clients.embedding import EmbeddingProviderFactory, OllamaEmbeddingProvider
from src.external.clients.errors import (
    ExternalServiceError,
    ServiceResponseError,
    ServiceValidationError,
)


class TestOllamaEmbeddingProvider:
    """Test cases for Ollama Embedding Provider."""

    @pytest.fixture
    def provider(self):
        """Create a new Ollama embedding provider instance for each test."""
        return OllamaEmbeddingProvider(base_url="http://localhost:11434", model="test-model")

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.base_url == "http://localhost:11434"
        assert provider.model == "test-model"
        assert provider.provider_name == "ollama"
        assert provider.model_name == "test-model"
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, provider):
        """Test connect and disconnect methods."""
        # Test connect
        await provider.connect()
        assert provider._client is not None

        # Test disconnect
        await provider.disconnect()
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_check_connection_success(self, provider):
        """Test successful connection check."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.get.return_value = mock_response
        provider._client = mock_client

        # Execute
        result = await provider.check_connection()

        # Verify
        assert result is True
        # Note: BaseHttpClient.get constructs full URL internally
        args, kwargs = mock_client.get.call_args
        assert args[0] == "http://localhost:11434/api/tags"

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, provider):
        """Test connection check failure."""
        # Setup
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        provider._client = mock_client

        # Execute
        result = await provider.check_connection()

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_get_embedding_success_embeddings_format(self, provider):
        """Test successful embedding retrieval with 'embeddings' format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}

        mock_client.post.return_value = mock_response
        provider._client = mock_client

        # Execute
        result = await provider.get_embedding("test text")

        # Verify
        assert result == [0.1, 0.2, 0.3]
        # Note: BaseHttpClient.post constructs full URL internally
        args, kwargs = mock_client.post.call_args
        assert args[0] == "http://localhost:11434/api/embed"
        assert kwargs["json"] == {"model": "test-model", "input": "test text"}
        assert kwargs["headers"] == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    async def test_get_embedding_success_embedding_format(self, provider):
        """Test successful embedding retrieval with 'embedding' format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.4, 0.5, 0.6]}

        mock_client.post.return_value = mock_response
        provider._client = mock_client

        # Execute
        result = await provider.get_embedding("test text")

        # Verify
        assert result == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_get_embedding_empty_text(self, provider):
        """Test embedding retrieval with empty text."""
        # Execute & Verify
        with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
            await provider.get_embedding("")

    @pytest.mark.asyncio
    async def test_get_embedding_whitespace_only_text(self, provider):
        """Test embedding retrieval with whitespace-only text."""
        # Execute & Verify
        with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
            await provider.get_embedding("   ")

    @pytest.mark.asyncio
    async def test_get_embedding_empty_embeddings_list(self, provider):
        """Test embedding retrieval with empty embeddings list."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": []}

        mock_client.post.return_value = mock_response
        provider._client = mock_client

        # Execute & Verify
        # Note: ServiceResponseError is wrapped in ExternalServiceError by handle_connection_error
        with pytest.raises(ExternalServiceError, match="Empty embeddings array"):
            await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_unexpected_format(self, provider):
        """Test embedding retrieval with unexpected response format."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"unknown_field": "value"}

        mock_client.post.return_value = mock_response
        provider._client = mock_client

        # Execute & Verify
        # Note: ServiceResponseError is wrapped in ExternalServiceError by handle_connection_error
        with pytest.raises(ExternalServiceError, match="Unexpected response format"):
            await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_http_status_error(self, provider):
        """Test embedding retrieval with HTTP status error."""
        # Setup
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        http_error = httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=mock_response)
        mock_client.post.side_effect = http_error
        provider._client = mock_client

        # Execute & Verify
        with pytest.raises(ExternalServiceError):
            await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_connection_error(self, provider):
        """Test embedding retrieval with connection error."""
        # Setup
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        provider._client = mock_client

        # Execute & Verify
        with pytest.raises(ExternalServiceError):
            await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_success(self, provider):
        """Test successful batch embedding retrieval."""
        # Setup
        provider.get_embedding = AsyncMock()
        provider.get_embedding.side_effect = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        texts = ["text1", "text2", "text3"]

        # Execute
        result = await provider.get_embeddings_batch(texts)

        # Verify
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        assert provider.get_embedding.call_count == 3
        provider.get_embedding.assert_any_call("text1")
        provider.get_embedding.assert_any_call("text2")
        provider.get_embedding.assert_any_call("text3")

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_empty_list(self, provider):
        """Test batch embedding retrieval with empty list raises validation error."""
        # Execute & Verify
        with pytest.raises(ServiceValidationError, match="Texts list cannot be empty"):
            await provider.get_embeddings_batch([])

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_partial_failure(self, provider):
        """Test batch embedding retrieval with partial failure."""
        # Setup
        provider.get_embedding = AsyncMock()
        provider.get_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            ServiceValidationError("Ollama", "Failed to get embedding"),
        ]

        texts = ["text1", "text2"]

        # Execute & Verify
        with pytest.raises(ServiceValidationError):
            await provider.get_embeddings_batch(texts)

        assert provider.get_embedding.call_count == 2

    def test_extract_embedding_from_response_embeddings_format(self, provider):
        """Test embedding extraction with embeddings format."""
        response_data = {"embeddings": [[0.1, 0.2, 0.3]]}
        result = provider._extract_embedding_from_response(response_data)
        assert result == [0.1, 0.2, 0.3]

    def test_extract_embedding_from_response_embedding_format(self, provider):
        """Test embedding extraction with embedding format."""
        response_data = {"embedding": [0.4, 0.5, 0.6]}
        result = provider._extract_embedding_from_response(response_data)
        assert result == [0.4, 0.5, 0.6]

    def test_extract_embedding_from_response_empty_embeddings(self, provider):
        """Test embedding extraction with empty embeddings."""
        response_data = {"embeddings": []}
        with pytest.raises(ServiceResponseError, match="Empty embeddings array"):
            provider._extract_embedding_from_response(response_data)

    def test_extract_embedding_from_response_missing_field(self, provider):
        """Test embedding extraction with missing field."""
        response_data = {"unknown": "value"}
        with pytest.raises(ServiceResponseError, match="Unexpected response format"):
            provider._extract_embedding_from_response(response_data)

    def test_repr(self, provider):
        """Test string representation of the provider."""
        expected = "OllamaEmbeddingProvider(base_url='http://localhost:11434', model='test-model')"
        assert repr(provider) == expected


class TestEmbeddingProviderFactory:
    """Test cases for EmbeddingProviderFactory."""

    def test_list_available_providers(self):
        """Test listing available providers."""
        providers = EmbeddingProviderFactory.list_available_providers()
        assert "ollama" in providers
        assert isinstance(providers, list)

    def test_create_ollama_provider(self):
        """Test creating Ollama provider."""
        provider = EmbeddingProviderFactory.create_provider(
            provider_type="ollama", base_url="http://test:11434", model="test-model"
        )
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.provider_name == "ollama"
        assert provider.base_url == "http://test:11434"
        assert provider.model_name == "test-model"

    def test_create_provider_defaults_to_ollama(self):
        """Test that create_provider defaults to Ollama."""
        provider = EmbeddingProviderFactory.create_provider()
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.provider_name == "ollama"

    def test_create_provider_unsupported_type(self):
        """Test creating provider with unsupported type."""
        with pytest.raises(ValueError, match="Unsupported embedding provider: unsupported"):
            EmbeddingProviderFactory.create_provider(provider_type="unsupported")

    def test_get_default_provider(self):
        """Test getting default provider."""
        provider = EmbeddingProviderFactory.get_default_provider()
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.provider_name == "ollama"
