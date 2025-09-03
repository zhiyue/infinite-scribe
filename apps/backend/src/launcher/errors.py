"""Custom exceptions for launcher module"""


class LauncherError(Exception):
    """Base exception for launcher errors"""

    pass


class DependencyNotReadyError(LauncherError):
    """Raised when a required dependency is not ready"""

    pass


class ServiceStartupError(LauncherError):
    """Raised when a service fails to start"""

    pass


class ServiceStopError(LauncherError):
    """Raised when a service fails to stop gracefully"""

    pass


class ConfigValidationError(LauncherError):
    """Raised when configuration validation fails"""

    pass


class OrchestrationError(LauncherError):
    """Raised when service orchestration fails"""

    pass


class HealthCheckError(LauncherError):
    """Raised when health check fails"""

    pass


class ApiStartError(LauncherError):
    """Raised when API Gateway fails to start"""

    pass


class AgentsStartError(LauncherError):
    """Raised when Agent services fail to start"""

    pass
