"""Exception definitions for external service clients."""

import httpx


class ExternalServiceError(Exception):
    """Base exception for external service errors."""

    def __init__(self, service_name: str, message: str, original_error: Exception | None = None):
        """Initialize external service error.

        Args:
            service_name: Name of the external service
            message: Error message
            original_error: Original exception that caused this error
        """
        self.service_name = service_name
        self.original_error = original_error
        super().__init__(f"{service_name}: {message}")


class ServiceUnavailableError(ExternalServiceError):
    """Raised when external service is unavailable or unreachable."""

    def __init__(self, service_name: str, original_error: Exception | None = None):
        super().__init__(
            service_name=service_name, message="Service is unavailable or unreachable", original_error=original_error
        )


class ServiceConnectionError(ExternalServiceError):
    """Raised when connection to external service fails."""

    def __init__(self, service_name: str, original_error: Exception | None = None):
        super().__init__(
            service_name=service_name, message="Failed to connect to service", original_error=original_error
        )


class ServiceAuthenticationError(ExternalServiceError):
    """Raised when authentication with external service fails."""

    def __init__(self, service_name: str, original_error: Exception | None = None):
        super().__init__(service_name=service_name, message="Authentication failed", original_error=original_error)


class ServiceRateLimitError(ExternalServiceError):
    """Raised when external service rate limit is exceeded."""

    def __init__(self, service_name: str, retry_after: int | None = None, original_error: Exception | None = None):
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"

        super().__init__(service_name=service_name, message=message, original_error=original_error)


class ServiceValidationError(ExternalServiceError):
    """Raised when service request validation fails."""

    def __init__(self, service_name: str, validation_details: str, original_error: Exception | None = None):
        self.validation_details = validation_details
        super().__init__(
            service_name=service_name,
            message=f"Request validation failed: {validation_details}",
            original_error=original_error,
        )


class ServiceResponseError(ExternalServiceError):
    """Raised when service returns unexpected response format."""

    def __init__(self, service_name: str, response_details: str, original_error: Exception | None = None):
        self.response_details = response_details
        super().__init__(
            service_name=service_name,
            message=f"Unexpected response format: {response_details}",
            original_error=original_error,
        )


def handle_http_error(service_name: str, error: httpx.HTTPStatusError) -> ExternalServiceError:
    """Convert HTTP error to appropriate service error.

    Args:
        service_name: Name of the external service
        error: HTTP status error

    Returns:
        Appropriate external service error
    """
    status_code = error.response.status_code

    if status_code == 401:
        return ServiceAuthenticationError(service_name, error)
    elif status_code == 429:
        retry_after = error.response.headers.get("Retry-After")
        retry_after_int = int(retry_after) if retry_after and retry_after.isdigit() else None
        return ServiceRateLimitError(service_name, retry_after_int, error)
    elif status_code == 422:
        return ServiceValidationError(service_name, f"HTTP {status_code} - {error.response.text}", error)
    elif status_code >= 500:
        return ServiceUnavailableError(service_name, error)
    else:
        return ExternalServiceError(service_name, f"HTTP {status_code} - {error.response.text}", error)


def handle_connection_error(service_name: str, error: Exception) -> ExternalServiceError:
    """Convert connection error to appropriate service error.

    Args:
        service_name: Name of the external service
        error: Connection error

    Returns:
        Appropriate external service error
    """
    if isinstance(error, httpx.ConnectError):
        return ServiceConnectionError(service_name, error)
    elif isinstance(error, httpx.TimeoutException):
        return ServiceUnavailableError(service_name, error)
    else:
        return ExternalServiceError(service_name, str(error), error)
