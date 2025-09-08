"""Abstract base class for embedding providers."""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base class for embedding service providers.

    This interface allows switching between different embedding providers
    (Ollama, OpenAI, Anthropic, etc.) while maintaining consistent behavior.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the embedding service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the embedding service."""
        pass

    @abstractmethod
    async def check_connection(self) -> bool:
        """Check if embedding service is accessible.

        Returns:
            True if service is accessible, False otherwise
        """
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Get vector representation of text.

        Args:
            text: Text to embed

        Returns:
            List of embedding values

        Raises:
            ServiceValidationError: If text is invalid
            ServiceResponseError: If service response is unexpected
            ExternalServiceError: For other service errors
        """
        pass

    @abstractmethod
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get vector representations for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ServiceValidationError: If texts list is invalid
            ExternalServiceError: For service errors
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the embedding provider (e.g., 'ollama', 'openai')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        pass


class EmbeddingClient(EmbeddingProvider):
    """Alias for backward compatibility."""

    pass
