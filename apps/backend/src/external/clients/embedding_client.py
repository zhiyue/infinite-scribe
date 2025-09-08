"""Embedding client for text vectorization using external embedding API."""

import logging
from typing import Any

import httpx
from src.core.config import settings

from .base_http import BaseHttpClient
from .errors import (
    ServiceResponseError,
    ServiceValidationError,
    handle_connection_error,
    handle_http_error,
)

logger = logging.getLogger(__name__)


class EmbeddingClient(BaseHttpClient):
    """Client for interacting with external embedding API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize embedding client.

        Args:
            base_url: Base URL for embedding API (defaults to settings)
            model: Model name for embedding API (defaults to settings)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.embedding_api_url
        self.model = model or settings.embedding_api_model

        super().__init__(
            base_url=self.base_url,
            timeout=timeout,
            max_keepalive_connections=5,
            max_connections=10,
        )

    async def check_connection(self) -> bool:
        """Check if embedding API is accessible.

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            response = await self.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Embedding API connection check failed: {e}")
            return False

    async def get_embedding(self, text: str) -> list[float]:
        """Get vector representation of text.

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
            raise ServiceValidationError("EmbeddingAPI", "Text cannot be empty")

        try:
            payload = {"model": self.model, "input": text}

            response = await self.post("/api/embed", json_data=payload, headers={"Content-Type": "application/json"})

            result = response.json()
            return self._extract_embedding_from_response(result)

        except httpx.HTTPStatusError as e:
            raise handle_http_error("EmbeddingAPI", e) from e
        except Exception as e:
            raise handle_connection_error("EmbeddingAPI", e) from e

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get vector representations for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ServiceValidationError: If texts list is empty
            ExternalServiceError: For API errors
        """
        if not texts:
            raise ServiceValidationError("EmbeddingAPI", "Texts list cannot be empty")

        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)

        logger.info(f"Generated embeddings for {len(texts)} texts")
        return embeddings

    def _extract_embedding_from_response(self, response_data: dict[str, Any]) -> list[float]:
        """Extract embedding vector from API response.

        Args:
            response_data: JSON response from embedding API

        Returns:
            Embedding vector

        Raises:
            ServiceResponseError: If response format is unexpected
        """
        try:
            # Try multiple response formats
            if "embeddings" in response_data:
                embeddings = response_data["embeddings"]
                if not embeddings:
                    raise ServiceResponseError("EmbeddingAPI", "Empty embeddings array")
                return embeddings[0]
            elif "embedding" in response_data:
                return response_data["embedding"]
            else:
                raise ServiceResponseError(
                    "EmbeddingAPI",
                    f"Unexpected response format, missing 'embeddings' or 'embedding' field: {response_data}",
                )
        except (KeyError, IndexError, TypeError) as e:
            raise ServiceResponseError("EmbeddingAPI", f"Failed to parse embedding response: {response_data}") from e

    def __repr__(self) -> str:
        """String representation of the client."""
        return f"EmbeddingClient(base_url='{self.base_url}', model='{self.model}')"


# Create global instance for backward compatibility
embedding_client = EmbeddingClient()

# Legacy alias for backward compatibility
embedding_service = embedding_client
