"""Ollama embedding provider implementation."""

import asyncio
import logging
from typing import Any

import httpx
from src.core.config import settings

from ..base_http import BaseHttpClient
from ..errors import (
    ServiceResponseError,
    ServiceValidationError,
    handle_connection_error,
    handle_http_error,
)
from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider, BaseHttpClient):
    """Ollama embedding service provider implementation.

    This provider connects to Ollama's embedding API to generate text embeddings.
    Ollama is a local/self-hosted solution for running embedding models.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize Ollama embedding provider.

        Args:
            base_url: Base URL for Ollama API (defaults to settings)
            model: Model name for embedding API (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.embedding_api_url
        self.model = model or settings.embedding_api_model

        # Initialize the BaseHttpClient
        BaseHttpClient.__init__(
            self,
            base_url=self.base_url,
            timeout=timeout,
            max_keepalive_connections=5,
            max_connections=10,
        )

    @property
    def provider_name(self) -> str:
        """Name of the embedding provider."""
        return "ollama"

    @property
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        return self.model

    async def connect(self) -> None:
        """Establish connection to the Ollama embedding service.

        Delegates to BaseHttpClient's connect method.
        """
        await BaseHttpClient.connect(self)

    async def disconnect(self) -> None:
        """Close connection to the Ollama embedding service.

        Delegates to BaseHttpClient's disconnect method.
        """
        await BaseHttpClient.disconnect(self)

    async def check_connection(self) -> bool:
        """Check if Ollama embedding API is accessible.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            response = await self.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama API connection check failed: {e}")
            return False

    async def get_embedding(self, text: str) -> list[float]:
        """Get vector representation of text from Ollama.

        Args:
            text: Text to embed

        Returns:
            List of embedding values

        Raises:
            ServiceValidationError: If text is empty or too long
            ServiceResponseError: If API response format is unexpected
            ExternalServiceError: For other API errors
        """
        if not text.strip():
            raise ServiceValidationError("Ollama", "Text cannot be empty")

        try:
            payload = {"model": self.model, "input": text}

            response = await self.post("/api/embed", json_data=payload, headers={"Content-Type": "application/json"})

            result = response.json()
            return self._extract_embedding_from_response(result)

        except ServiceResponseError:
            raise
        except httpx.HTTPStatusError as e:
            raise handle_http_error("Ollama", e) from e
        except Exception as e:
            raise handle_connection_error("Ollama", e) from e

    async def get_embeddings_batch(self, texts: list[str], concurrency: int = 1) -> list[list[float]]:
        """Get vector representations for multiple texts from Ollama.

        Args:
            texts: List of texts to embed
            concurrency: Maximum concurrent requests (default: 1 for sequential processing)

        Returns:
            List of embedding vectors in same order as input texts

        Raises:
            ServiceValidationError: If texts list is empty
            ExternalServiceError: For API errors
        """
        if not texts:
            raise ServiceValidationError("Ollama", "Texts list cannot be empty")

        if concurrency <= 1:
            # Sequential processing (default behavior for stability)
            embeddings = []
            for text in texts:
                embedding = await self.get_embedding(text)
                embeddings.append(embedding)
        else:
            # Bounded concurrent processing
            semaphore = asyncio.Semaphore(concurrency)

            async def get_embedding_with_semaphore(text: str, index: int) -> tuple[int, list[float]]:
                """Get embedding with concurrency control and preserve order."""
                async with semaphore:
                    try:
                        embedding = await self.get_embedding(text)
                        return index, embedding
                    except Exception as e:
                        logger.warning(f"Failed to get embedding for text at index {index}: {e}")
                        raise

            # Process all texts concurrently with bounded semaphore
            tasks = [get_embedding_with_semaphore(text, i) for i, text in enumerate(texts)]

            try:
                results = await asyncio.gather(*tasks)
                # Sort by original index to maintain order
                results.sort(key=lambda x: x[0])
                embeddings = [result[1] for result in results]
            except Exception as e:
                logger.error(f"Batch embedding failed with concurrency {concurrency}: {e}")
                raise

        logger.info(f"Generated embeddings for {len(texts)} texts using Ollama (concurrency: {concurrency})")
        return embeddings

    def _extract_embedding_from_response(self, response_data: dict[str, Any]) -> list[float]:
        """Extract embedding vector from Ollama API response.

        Ollama API returns embeddings in specific formats that may vary.

        Args:
            response_data: JSON response from Ollama API

        Returns:
            Embedding vector

        Raises:
            ServiceResponseError: If response format is unexpected
        """
        try:
            # Ollama API response formats
            if "embeddings" in response_data:
                embeddings = response_data["embeddings"]
                if not embeddings:
                    raise ServiceResponseError("Ollama", "Empty embeddings array")
                return embeddings[0]
            elif "embedding" in response_data:
                return response_data["embedding"]
            else:
                raise ServiceResponseError(
                    "Ollama",
                    f"Unexpected response format, missing 'embeddings' or 'embedding' field: {response_data}",
                )
        except (KeyError, IndexError, TypeError) as e:
            raise ServiceResponseError("Ollama", f"Failed to parse embedding response: {response_data}") from e

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"OllamaEmbeddingProvider(base_url='{self.base_url}', model='{self.model}')"
