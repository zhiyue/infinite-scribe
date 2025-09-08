"""Embedding providers package.

This package provides a unified interface for different embedding service providers,
allowing easy switching between Ollama, OpenAI, Anthropic, and other providers.
"""

from .base import EmbeddingProvider
from .factory import EmbeddingProviderFactory
from .ollama import OllamaEmbeddingProvider

# Cache for lazy initialization
_default_provider_cache: EmbeddingProvider | None = None


def get_embedding_service() -> EmbeddingProvider:
    """Get default embedding service with lazy initialization.

    Returns:
        Default embedding provider instance
    """
    global _default_provider_cache
    if _default_provider_cache is None:
        _default_provider_cache = EmbeddingProviderFactory.get_default_provider()
    return _default_provider_cache


__all__ = [
    # Abstract base
    "EmbeddingProvider",
    # Concrete providers
    "OllamaEmbeddingProvider",
    # Factory
    "EmbeddingProviderFactory",
    # Recommended interface
    "get_embedding_service",
]
