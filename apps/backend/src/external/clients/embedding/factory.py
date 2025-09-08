"""Factory for creating embedding providers."""

import logging

from src.core.config import settings

from .base import EmbeddingProvider
from .ollama import OllamaEmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingProviderFactory:
    """Factory class for creating embedding providers."""

    _providers: dict[str, type[EmbeddingProvider]] = {
        "ollama": OllamaEmbeddingProvider,
        # Future providers can be added here:
        # "openai": OpenAIEmbeddingProvider,
        # "anthropic": AnthropicEmbeddingProvider,
        # "huggingface": HuggingFaceEmbeddingProvider,
    }

    @classmethod
    def create_provider(
        cls, provider_type: str | None = None, base_url: str | None = None, model: str | None = None, **kwargs
    ) -> EmbeddingProvider:
        """Create an embedding provider instance.

        Args:
            provider_type: Type of provider ('ollama', 'openai', etc.).
                         Defaults to 'ollama'
            base_url: Base URL for the provider API
            model: Model name to use
            **kwargs: Additional provider-specific arguments

        Returns:
            Configured embedding provider instance

        Raises:
            ValueError: If provider_type is not supported
        """
        provider_type = provider_type or "ollama"

        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unsupported embedding provider: {provider_type}. " f"Available providers: {available}")

        provider_class = cls._providers[provider_type]
        logger.info(f"Creating {provider_type} embedding provider")

        # Collect all parameters for the provider
        provider_kwargs = {}
        if base_url is not None:
            provider_kwargs["base_url"] = base_url
        if model is not None:
            provider_kwargs["model"] = model
        provider_kwargs.update(kwargs)

        return provider_class(**provider_kwargs)

    @classmethod
    def get_default_provider(cls) -> EmbeddingProvider:
        """Get the default embedding provider configured in settings.

        Returns:
            Default embedding provider instance
        """
        config = settings.embedding.provider_config
        return cls.create_provider(provider_type=settings.embedding.provider, **config)

    @classmethod
    def register_provider(cls, name: str, provider_class: type[EmbeddingProvider]) -> None:
        """Register a new embedding provider.

        This allows third-party or custom providers to be added dynamically.

        Args:
            name: Name of the provider
            provider_class: Provider class that implements EmbeddingProvider
        """
        if not issubclass(provider_class, EmbeddingProvider):
            raise ValueError(f"Provider class {provider_class} must implement EmbeddingProvider")

        cls._providers[name] = provider_class
        logger.info(f"Registered new embedding provider: {name}")

    @classmethod
    def list_available_providers(cls) -> list[str]:
        """List all available embedding provider types.

        Returns:
            List of provider type names
        """
        return list(cls._providers.keys())
