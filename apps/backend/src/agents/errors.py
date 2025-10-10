"""Agent error classification types."""


class RetriableError(Exception):
    """Errors that should be retried according to retry policy."""


class NonRetriableError(Exception):
    """Errors that should not be retried and go directly to DLT."""
