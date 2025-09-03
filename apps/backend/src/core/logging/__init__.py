"""
Unified backend logging module

Provides full backend common structured logging configuration and interface
"""

from .config import configure_logging, get_logger
from .context import bind_request_context, bind_service_context, clear_context, get_current_context
from .types import ErrorType

# Export unified interface
__all__ = [
    # Core interface
    "configure_logging",
    "get_logger",
    # Context binding
    "bind_request_context",
    "bind_service_context",
    "get_current_context",
    "clear_context",
    # Type definitions
    "ErrorType",
    # Note: ComponentType should be imported directly from launcher.types
    # to maintain proper dependency direction: core should not depend on launcher
]

# Version information
__version__ = "1.0.0"
