"""External service clients package.

This package contains clients for interacting with external services following
Clean/Hexagonal architecture principles.
"""

from .base_http import BaseHttpClient
from .embedding import (
    EmbeddingProvider,
    EmbeddingProviderFactory,
    OllamaEmbeddingProvider,
    get_embedding_service,
)
from .errors import (
    ExternalServiceError,
    ServiceAuthenticationError,
    ServiceConnectionError,
    ServiceRateLimitError,
    ServiceResponseError,
    ServiceUnavailableError,
    ServiceValidationError,
    handle_connection_error,
    handle_http_error,
)

__all__ = [
    # Base classes
    "BaseHttpClient",
    # Embedding providers
    "EmbeddingProvider",
    "OllamaEmbeddingProvider",
    "EmbeddingProviderFactory",
    # Embedding service
    "get_embedding_service",
    # Exceptions
    "ExternalServiceError",
    "ServiceUnavailableError",
    "ServiceConnectionError",
    "ServiceAuthenticationError",
    "ServiceRateLimitError",
    "ServiceValidationError",
    "ServiceResponseError",
    # Error handlers
    "handle_http_error",
    "handle_connection_error",
]
