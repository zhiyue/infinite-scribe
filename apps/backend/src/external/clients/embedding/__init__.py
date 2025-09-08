"""Embedding providers package.

This package provides a unified interface for different embedding service providers,
allowing easy switching between Ollama, OpenAI, Anthropic, and other providers.
"""

from .base import EmbeddingClient, EmbeddingProvider  # EmbeddingClient for backward compatibility
from .factory import EmbeddingProviderFactory
from .ollama import OllamaEmbeddingProvider

# Cache for lazy initialization
_default_provider_cache = None


def get_embedding_service() -> EmbeddingProvider:
    """Get default embedding service with lazy initialization.

    Returns:
        Default embedding provider instance
    """
    global _default_provider_cache
    if _default_provider_cache is None:
        _default_provider_cache = EmbeddingProviderFactory.get_default_provider()
    return _default_provider_cache


def get_embedding_client() -> EmbeddingProvider:
    """Get default embedding client (legacy alias for get_embedding_service).

    Returns:
        Default embedding provider instance
    """
    return get_embedding_service()


# Legacy support - create lazy instances that warn about deprecation
def _get_legacy_service():
    """Get service with deprecation warning."""
    import warnings

    warnings.warn(
        "Direct property access to 'embedding_service' is deprecated. "
        "Use 'get_embedding_service()' function instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    return get_embedding_service()


def _get_legacy_client():
    """Get client with deprecation warning."""
    import warnings

    warnings.warn(
        "Direct property access to 'embedding_client' is deprecated. " "Use 'get_embedding_client()' function instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    return get_embedding_client()


# Create lazy module-level instances for backward compatibility
# These will issue deprecation warnings when accessed
class _LazyInstance:
    def __init__(self, factory_func):
        self._factory = factory_func
        self._instance = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = self._factory()
        return getattr(self._instance, name)

    def __call__(self, *args, **kwargs):
        if self._instance is None:
            self._instance = self._factory()
        return self._instance(*args, **kwargs)


embedding_service = _LazyInstance(_get_legacy_service)
embedding_client = _LazyInstance(_get_legacy_client)


__all__ = [
    # Abstract base
    "EmbeddingProvider",
    "EmbeddingClient",  # Backward compatibility alias
    # Concrete providers
    "OllamaEmbeddingProvider",
    # Factory
    "EmbeddingProviderFactory",
    # Lazy initialization functions (recommended)
    "get_embedding_service",
    "get_embedding_client",
    # Legacy support (deprecated but kept for compatibility)
    "embedding_client",
    "embedding_service",
]
