"""Integration tests for OllamaEmbeddingProvider against real Ollama service.

These tests run against a real Ollama instance and are configured to:
- Only run locally (not in CI)
- Test real embedding functionality
- Verify service connectivity and health

Note: These tests intentionally bypass the standard integration test fixtures
to avoid conflicts with email service mocking and other shared fixtures.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from src.external.clients.embedding.ollama import OllamaEmbeddingProvider
from src.external.clients.errors import ExternalServiceError, ServiceValidationError

# Skip tests in CI environment
pytestmark = [
    pytest.mark.skipif(
        os.getenv("CI") is not None or os.getenv("GITHUB_ACTIONS") is not None,
        reason="Ollama integration tests only run locally",
    ),
    pytest.mark.integration,
]


class TestOllamaEmbeddingIntegration:
    """Integration tests for OllamaEmbeddingProvider using real Ollama service."""

    @pytest.fixture
    def base_url(self):
        """Base URL for local Ollama instance."""
        return os.getenv("TEST_OLLAMA_URL", "http://127.0.0.1:11434")

    @pytest.fixture
    def model_name(self):
        """Model name for testing - use a lightweight model."""
        return os.getenv("TEST_OLLAMA_MODEL", "dengcao/Qwen3-Embedding-0.6B:F16")

    @pytest.fixture
    async def provider(self, base_url, model_name) -> AsyncGenerator[OllamaEmbeddingProvider, None]:
        """Create and initialize OllamaEmbeddingProvider for testing."""
        provider = OllamaEmbeddingProvider(base_url=base_url, model=model_name)
        await provider.connect()
        yield provider
        await provider.disconnect()

    @pytest.fixture
    def skip_if_ollama_unavailable(self, provider):
        """Skip test if Ollama service is not available."""

        async def check():
            try:
                is_available = await provider.check_connection()
                if not is_available:
                    pytest.skip("Ollama service is not available")
            except Exception:
                pytest.skip("Cannot connect to Ollama service")

        return check

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_connection_health_check(self, provider: OllamaEmbeddingProvider):
        """Test that we can connect to real Ollama instance."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available at configured URL")

        assert is_connected is True
        assert provider.provider_name == "ollama"

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_single_embedding_generation(self, provider: OllamaEmbeddingProvider):
        """Test generating embedding for a single text."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        text = "This is a test sentence for embedding generation."

        embedding = await provider.get_embedding(text)

        # Verify embedding properties
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, int | float) for x in embedding)

        # Typical embedding dimensions for nomic-embed-text is 768
        # But we'll be flexible since different models have different dimensions
        assert 64 <= len(embedding) <= 4096, f"Unexpected embedding dimension: {len(embedding)}"

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_batch_embedding_generation(self, provider: OllamaEmbeddingProvider):
        """Test generating embeddings for multiple texts."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        texts = [
            "First test sentence for batch embedding.",
            "Second test sentence with different content.",
            "Third sentence to complete the batch test.",
        ]

        embeddings = await provider.get_embeddings_batch(texts)

        # Verify batch results
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)

        for i, embedding in enumerate(embeddings):
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            assert all(isinstance(x, int | float) for x in embedding)

            # All embeddings should have the same dimension
            if i > 0:
                assert len(embedding) == len(
                    embeddings[0]
                ), f"Embedding {i} has different dimension than first embedding"

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_embedding_consistency(self, provider: OllamaEmbeddingProvider):
        """Test that same text produces consistent embeddings."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        text = "Consistency test sentence."

        # Generate embedding twice
        embedding1 = await provider.get_embedding(text)
        embedding2 = await provider.get_embedding(text)

        # Embeddings should be identical for the same text
        assert len(embedding1) == len(embedding2)

        # Allow for small floating point differences
        for i, (val1, val2) in enumerate(zip(embedding1, embedding2, strict=False)):
            assert abs(val1 - val2) < 1e-6, f"Embedding inconsistency at index {i}: {val1} != {val2}"

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_different_texts_different_embeddings(self, provider: OllamaEmbeddingProvider):
        """Test that different texts produce different embeddings."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        text1 = "This is about cats and their behavior."
        text2 = "Machine learning algorithms are fascinating."

        embedding1 = await provider.get_embedding(text1)
        embedding2 = await provider.get_embedding(text2)

        # Embeddings should be different
        assert len(embedding1) == len(embedding2)

        # Calculate simple distance - embeddings should not be identical
        differences = sum(abs(v1 - v2) for v1, v2 in zip(embedding1, embedding2, strict=False))
        assert differences > 0.01, "Embeddings are too similar for different texts"

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_unicode_text_embedding(self, provider: OllamaEmbeddingProvider):
        """Test embedding generation with Unicode text."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        texts = ["Hello world! 🌍", "Café naïve résumé", "中文测试句子", "العربية اختبار", "Тест на русском языке"]

        for text in texts:
            embedding = await provider.get_embedding(text)
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            assert all(isinstance(x, int | float) for x in embedding)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_long_text_embedding(self, provider: OllamaEmbeddingProvider):
        """Test embedding generation with longer text."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        # Create a longer text (but not too long to avoid timeouts)
        long_text = " ".join(
            [
                "This is a longer text passage for testing embedding generation.",
                "It contains multiple sentences and various concepts.",
                "The purpose is to verify that the embedding service can handle",
                "reasonably sized text inputs without issues.",
                "This should still be within typical embedding model limits.",
            ]
        )

        embedding = await provider.get_embedding(long_text)
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, int | float) for x in embedding)

    @pytest.mark.integration
    async def test_validation_errors_still_work(self, provider: OllamaEmbeddingProvider):
        """Test that validation errors work even with real service."""
        # These should fail validation before reaching the service
        with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
            await provider.get_embedding("")

        with pytest.raises(ServiceValidationError, match="Text cannot be empty"):
            await provider.get_embedding("   \t\n   ")

        with pytest.raises(ServiceValidationError, match="Texts list cannot be empty"):
            await provider.get_embeddings_batch([])

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_service_error_handling(self, provider: OllamaEmbeddingProvider, model_name: str):
        """Test error handling with invalid model name."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        # Create provider with invalid model
        invalid_provider = OllamaEmbeddingProvider(base_url=provider.base_url, model="invalid-model-name-12345")

        await invalid_provider.connect()
        try:
            with pytest.raises(ExternalServiceError):
                await invalid_provider.get_embedding("test text")
        finally:
            await invalid_provider.disconnect()

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_requests(self, provider: OllamaEmbeddingProvider):
        """Test concurrent embedding requests."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        import asyncio

        texts = [f"Concurrent test sentence number {i}." for i in range(5)]

        # Make concurrent requests
        tasks = [provider.get_embedding(text) for text in texts]
        embeddings = await asyncio.gather(*tasks)

        # Verify all embeddings were generated correctly
        assert len(embeddings) == len(texts)
        for embedding in embeddings:
            assert isinstance(embedding, list)
            assert len(embedding) > 0
            assert all(isinstance(x, int | float) for x in embedding)

    @pytest.mark.integration
    @pytest.mark.slow
    async def test_provider_properties(self, provider: OllamaEmbeddingProvider, model_name: str):
        """Test provider properties and string representation."""
        # Skip if service unavailable
        is_connected = await provider.check_connection()
        if not is_connected:
            pytest.skip("Ollama service is not available")

        assert provider.provider_name == "ollama"
        assert provider.model_name == model_name

        # Test string representation
        repr_str = repr(provider)
        assert "OllamaEmbeddingProvider" in repr_str
        assert provider.base_url in repr_str
        assert model_name in repr_str
