"""Component tests for OllamaEmbeddingProvider.

Component tests verify behavior by using real instances with mocked external dependencies.
These tests use pytest-httpx to mock HTTP responses instead of mocking internal methods.
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from src.external.clients.embedding.ollama import OllamaEmbeddingProvider
from src.external.clients.errors import ExternalServiceError, ServiceValidationError


class TestOllamaEmbeddingProviderComponent:
    """Component tests for OllamaEmbeddingProvider using HTTP mocking."""

    @pytest.fixture
    def base_url(self):
        """Base URL for Ollama API testing."""
        return "http://localhost:11434"

    @pytest.fixture
    def model_name(self):
        """Model name for testing."""
        return "nomic-embed-text"

    @pytest.fixture
    def provider(self, base_url, model_name):
        """Create an OllamaEmbeddingProvider instance for testing."""
        return OllamaEmbeddingProvider(base_url=base_url, model=model_name)

    @pytest.fixture
    def sample_embedding(self):
        """Sample embedding vector for testing."""
        return [0.1, 0.2, 0.3, -0.4, 0.5]

    @pytest.fixture
    def ollama_embeddings_response(self, sample_embedding):
        """Sample Ollama API response with 'embeddings' format."""
        return {"embeddings": [sample_embedding]}

    @pytest.fixture
    def ollama_embedding_response(self, sample_embedding):
        """Sample Ollama API response with 'embedding' format."""
        return {"embedding": sample_embedding}

    @pytest.mark.asyncio
    async def test_provider_initialization(self, provider, base_url, model_name):
        """Test provider initializes with correct configuration."""
        assert provider.base_url == base_url
        assert provider.model == model_name
        assert provider.provider_name == "ollama"
        assert provider.model_name == model_name

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, provider):
        """Test connect and disconnect operations."""
        # Initially not connected
        assert provider._client is None

        # Connect
        await provider.connect()
        assert provider._client is not None

        # Disconnect
        await provider.disconnect()
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_check_connection_success(self, provider, base_url, httpx_mock):
        """Test successful connection check."""
        # Mock successful /api/tags response
        httpx_mock.add_response(
            url=f"{base_url}/api/tags",
            json={"models": [{"name": "nomic-embed-text"}]},
            status_code=200,
        )

        async with provider.session():
            is_connected = await provider.check_connection()
            assert is_connected is True

        # Verify the request was made to correct endpoint
        request = httpx_mock.get_request()
        assert "/api/tags" in request.url.path

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, provider, base_url, httpx_mock):
        """Test connection check failure."""
        # Mock connection error
        httpx_mock.add_exception(
            url=f"{base_url}/api/tags",
            exception=httpx.ConnectError("Connection failed"),
        )

        async with provider.session():
            is_connected = await provider.check_connection()
            assert is_connected is False

    @pytest.mark.asyncio
    async def test_check_connection_http_error(self, provider, base_url, httpx_mock):
        """Test connection check with HTTP error."""
        # Mock HTTP error response
        httpx_mock.add_response(
            url=f"{base_url}/api/tags",
            json={"error": "Service unavailable"},
            status_code=503,
        )

        async with provider.session():
            is_connected = await provider.check_connection()
            assert is_connected is False

    @pytest.mark.asyncio
    async def test_get_embedding_success_embeddings_format(
        self, provider, base_url, model_name, httpx_mock, ollama_embeddings_response, sample_embedding
    ):
        """Test successful embedding with 'embeddings' response format."""
        text = "Hello world"

        # Mock successful embedding response
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json=ollama_embeddings_response,
            status_code=200,
        )

        async with provider.session():
            result = await provider.get_embedding(text)

        assert result == sample_embedding

        # Verify request payload
        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert "/api/embed" in request.url.path

        payload = json.loads(request.content)
        assert payload == {"model": model_name, "input": text}
        assert request.headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_get_embedding_success_embedding_format(
        self, provider, base_url, httpx_mock, ollama_embedding_response, sample_embedding
    ):
        """Test successful embedding with 'embedding' response format."""
        text = "Hello world"

        # Mock successful embedding response
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json=ollama_embedding_response,
            status_code=200,
        )

        async with provider.session():
            result = await provider.get_embedding(text)

        assert result == sample_embedding

    @pytest.mark.asyncio
    async def test_get_embedding_validation_error_empty_text(self, provider):
        """Test embedding validation with empty text."""
        async with provider.session():
            with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
                await provider.get_embedding("")

    @pytest.mark.asyncio
    async def test_get_embedding_validation_error_whitespace_text(self, provider):
        """Test embedding validation with whitespace-only text."""
        async with provider.session():
            with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
                await provider.get_embedding("   \t\n   ")

    @pytest.mark.asyncio
    async def test_get_embedding_http_error_400(self, provider, base_url, httpx_mock):
        """Test embedding request with HTTP 400 error."""
        # Mock HTTP 400 error
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"error": "Invalid model name"},
            status_code=400,
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_http_error_500(self, provider, base_url, httpx_mock):
        """Test embedding request with HTTP 500 error."""
        # Mock HTTP 500 error
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"error": "Internal server error"},
            status_code=500,
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_connection_error(self, provider, base_url, httpx_mock):
        """Test embedding request with connection error."""
        # Mock connection error
        httpx_mock.add_exception(
            url=f"{base_url}/api/embed",
            exception=httpx.ConnectError("Connection refused"),
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_timeout_error(self, provider, base_url, httpx_mock):
        """Test embedding request with timeout error."""
        # Mock timeout error
        httpx_mock.add_exception(
            url=f"{base_url}/api/embed",
            exception=httpx.TimeoutException("Request timed out"),
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_invalid_response_format(self, provider, base_url, httpx_mock):
        """Test embedding with invalid response format."""
        # Mock response with unexpected format
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"unknown_field": "unexpected"},
            status_code=200,
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError, match="Unexpected response format"):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_empty_embeddings_array(self, provider, base_url, httpx_mock):
        """Test embedding with empty embeddings array."""
        # Mock response with empty embeddings
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"embeddings": []},
            status_code=200,
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError, match="Empty embeddings array"):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embedding_malformed_json(self, provider, base_url, httpx_mock):
        """Test embedding with malformed JSON response."""
        # Mock response with malformed JSON
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            text="invalid json{",
            status_code=200,
        )

        async with provider.session():
            with pytest.raises(ExternalServiceError):
                await provider.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_sequential(self, provider, base_url, httpx_mock, ollama_embeddings_response):
        """Test batch embedding processing in sequential mode."""
        texts = ["text1", "text2", "text3"]
        expected_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        # Mock responses for each text
        for _, embedding in enumerate(expected_embeddings):
            httpx_mock.add_response(
                url=f"{base_url}/api/embed",
                json={"embeddings": [embedding]},
                status_code=200,
            )

        # Mock settings to ensure sequential processing
        with patch("src.external.clients.embedding.ollama.settings") as mock_settings:
            mock_settings.embedding.default_concurrency = 1

            async with provider.session():
                results = await provider.get_embeddings_batch(texts)

        assert results == expected_embeddings

        # Verify all requests were made
        requests = httpx_mock.get_requests()
        assert len(requests) == 3

        # Verify request payloads
        for i, request in enumerate(requests):
            payload = json.loads(request.content)
            assert payload["input"] == texts[i]

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_concurrent(self, provider, base_url, httpx_mock, ollama_embeddings_response):
        """Test batch embedding processing in concurrent mode."""
        texts = ["text1", "text2", "text3"]
        expected_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]

        # Mock responses for each text (order may vary due to concurrency)
        for embedding in expected_embeddings:
            httpx_mock.add_response(
                url=f"{base_url}/api/embed",
                json={"embeddings": [embedding]},
                status_code=200,
            )

        # Mock settings to enable concurrent processing
        with patch("src.external.clients.embedding.ollama.settings") as mock_settings:
            mock_settings.embedding.default_concurrency = 3
            mock_settings.embedding.max_concurrency = 5

            async with provider.session():
                results = await provider.get_embeddings_batch(texts, concurrency=3)

        # Results should match expected (order preserved)
        assert len(results) == 3
        assert all(len(emb) == 3 for emb in results)  # Each embedding has 3 dimensions

        # Verify all requests were made
        requests = httpx_mock.get_requests()
        assert len(requests) == 3

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_empty_list(self, provider):
        """Test batch embedding with empty input list."""
        async with provider.session():
            with pytest.raises(ServiceValidationError, match="Texts list cannot be empty"):
                await provider.get_embeddings_batch([])

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_partial_failure(self, provider, base_url, httpx_mock):
        """Test batch embedding with partial failures."""
        texts = ["text1", "text2"]

        # Mock success for first, failure for second
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"embeddings": [[0.1, 0.2, 0.3]]},
            status_code=200,
        )
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"error": "Model not found"},
            status_code=404,
        )

        # Mock settings for sequential processing to ensure predictable order
        with patch("src.external.clients.embedding.ollama.settings") as mock_settings:
            mock_settings.embedding.default_concurrency = 1

            async with provider.session():
                # Should fail on the second request
                with pytest.raises(ExternalServiceError):
                    await provider.get_embeddings_batch(texts)

    @pytest.mark.asyncio
    async def test_embedding_with_custom_headers(self, provider, base_url, httpx_mock):
        """Test embedding request includes proper headers."""
        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"embedding": [0.1, 0.2, 0.3]},
            status_code=200,
        )

        async with provider.session():
            await provider.get_embedding("test text")

        request = httpx_mock.get_request()
        assert request.headers["Content-Type"] == "application/json"
        assert "X-Correlation-ID" in request.headers  # From BaseHttpClient

    @pytest.mark.asyncio
    async def test_embedding_with_special_characters(self, provider, base_url, httpx_mock):
        """Test embedding with text containing special characters."""
        text = "Hello 世界! 🌍 Special chars: @#$%^&*()"

        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"embedding": [0.1, 0.2, 0.3]},
            status_code=200,
        )

        async with provider.session():
            result = await provider.get_embedding(text)

        assert result == [0.1, 0.2, 0.3]

        # Verify text was properly encoded
        request = httpx_mock.get_request()
        payload = json.loads(request.content)
        assert payload["input"] == text

    @pytest.mark.asyncio
    async def test_embedding_with_long_text(self, provider, base_url, httpx_mock):
        """Test embedding with very long text."""
        text = "Lorem ipsum " * 1000  # Very long text

        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"embedding": [0.1, 0.2, 0.3]},
            status_code=200,
        )

        async with provider.session():
            result = await provider.get_embedding(text)

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_provider_metrics_collection(self, base_url, model_name, httpx_mock):
        """Test that metrics are collected for embedding requests."""
        metrics_hook = AsyncMock()
        provider = OllamaEmbeddingProvider(base_url=base_url, model=model_name, metrics_hook=metrics_hook)

        httpx_mock.add_response(
            url=f"{base_url}/api/embed",
            json={"embedding": [0.1, 0.2, 0.3]},
            status_code=200,
        )

        async with provider.session():
            await provider.get_embedding("test text")

        # Verify metrics hook was called with provider labels
        metrics_hook.assert_called_once()
        args, kwargs = metrics_hook.call_args
        assert "provider" in kwargs
        assert kwargs["provider"] == "ollama"
        assert "model" in kwargs
        assert kwargs["model"] == model_name

    def test_provider_string_representation(self, provider, base_url, model_name):
        """Test provider string representation."""
        expected = f"OllamaEmbeddingProvider(base_url='{base_url}', model='{model_name}')"
        assert repr(provider) == expected
        assert str(provider) == expected
