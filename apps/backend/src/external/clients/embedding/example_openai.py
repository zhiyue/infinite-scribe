"""Example OpenAI embedding provider implementation.

This is a template showing how to add new embedding providers.
This file is not part of the production codebase - it's an example only.
"""

import httpx
from src.core.logging import bind_service_context, get_logger

from ..base_http import BaseHttpClient
from ..errors import (
    ServiceResponseError,
    ServiceValidationError,
    handle_connection_error,
    handle_http_error,
)
from .base import EmbeddingProvider

# Initialize service context and logger
bind_service_context(service="external-clients", component="embedding-openai-example", version="1.0.0")
logger = get_logger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider, BaseHttpClient):
    """OpenAI embedding service provider implementation.

    This provider connects to OpenAI's embedding API to generate text embeddings.
    This is an EXAMPLE implementation showing the pattern.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            base_url: Base URL for OpenAI API (defaults to official API)
            model: Model name for embedding API (defaults to text-embedding-ada-002)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model or "text-embedding-ada-002"

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
        return "openai"

    @property
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        return self.model

    async def connect(self) -> None:
        """Establish connection to the OpenAI embedding service."""
        await BaseHttpClient.connect(self)

    async def disconnect(self) -> None:
        """Close connection to the OpenAI embedding service."""
        await BaseHttpClient.disconnect(self)

    async def check_connection(self) -> bool:
        """Check if OpenAI embedding API is accessible."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = await self.get("/models", headers=headers)
            return response.status_code == 200
        except Exception as e:
            logger.warning("OpenAI API connection check failed", error=str(e), api_url=self.base_url)
            return False

    async def get_embedding(self, text: str) -> list[float]:
        """Get vector representation of text from OpenAI.

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
            raise ServiceValidationError("OpenAI", "Text cannot be empty")

        try:
            payload = {"model": self.model, "input": text}

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            response = await self.post("/embeddings", json_data=payload, headers=headers)

            result = response.json()
            return self._extract_embedding_from_response(result)

        except httpx.HTTPStatusError as e:
            raise handle_http_error("OpenAI", e) from e
        except Exception as e:
            raise handle_connection_error("OpenAI", e) from e

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get vector representations for multiple texts from OpenAI.

        OpenAI supports batch processing, so we can send all texts at once.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ServiceValidationError: If texts list is empty
            ExternalServiceError: For API errors
        """
        if not texts:
            raise ServiceValidationError("OpenAI", "Texts list cannot be empty")

        try:
            payload = {"model": self.model, "input": texts}

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            response = await self.post("/embeddings", json_data=payload, headers=headers)

            result = response.json()
            embeddings = []

            for item in result.get("data", []):
                embeddings.append(item["embedding"])

            logger.info("Generated embeddings batch", batch_size=len(texts), provider="openai", model=self.model)
            return embeddings

        except httpx.HTTPStatusError as e:
            raise handle_http_error("OpenAI", e) from e
        except Exception as e:
            raise handle_connection_error("OpenAI", e) from e

    def _extract_embedding_from_response(self, response_data) -> list[float]:
        """Extract embedding vector from OpenAI API response.

        Args:
            response_data: JSON response from OpenAI API

        Returns:
            Embedding vector

        Raises:
            ServiceResponseError: If response format is unexpected
        """
        try:
            data = response_data.get("data", [])
            if not data:
                raise ServiceResponseError("OpenAI", "No embedding data in response")

            return data[0]["embedding"]

        except (KeyError, IndexError, TypeError) as e:
            raise ServiceResponseError("OpenAI", f"Failed to parse embedding response: {response_data}") from e

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"OpenAIEmbeddingProvider(base_url='{self.base_url}', model='{self.model}')"


# Example of how to register the new provider:
# from .factory import EmbeddingProviderFactory
# EmbeddingProviderFactory.register_provider("openai", OpenAIEmbeddingProvider)
