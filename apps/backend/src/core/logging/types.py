"""Type definitions for logging module"""

from enum import Enum


class ErrorType(Enum):
    """Error type enumeration for standardized error classification"""

    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    CONFIG_ERROR = "config_error"
    DEPENDENCY_ERROR = "dependency_error"
    VALIDATION_ERROR = "validation_error"
    STARTUP_ERROR = "startup_error"
    SHUTDOWN_ERROR = "shutdown_error"
