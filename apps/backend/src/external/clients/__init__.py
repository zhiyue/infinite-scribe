"""External service clients package.

This package contains clients for interacting with external services following
Clean/Hexagonal architecture principles.
"""

from .base_http import BaseHttpClient
from .embedding_client import EmbeddingClient, embedding_client, embedding_service
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
    # Client implementations
    "EmbeddingClient",
    # Global instances
    "embedding_client",
    "embedding_service",  # Legacy alias
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
