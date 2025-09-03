"""Core logging configuration module"""

import logging
import threading
from typing import Any, Optional

import structlog

# Supported log levels for validation
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class LoggingConfigManager:
    """Thread-safe logging configuration manager (singleton)"""

    _instance: Optional["LoggingConfigManager"] = None
    _lock = threading.Lock()

    # Instance attributes (set in __new__)
    _configured: bool
    _config_lock: threading.Lock

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._configured = False
                    cls._instance._config_lock = threading.Lock()
        return cls._instance

    def is_configured(self) -> bool:
        """Check if logging is already configured"""
        with self._config_lock:
            return self._configured

    def set_configured(self, configured: bool = True) -> None:
        """Set configuration status"""
        with self._config_lock:
            self._configured = configured

    def reset(self) -> None:
        """Reset configuration state (mainly for testing)"""
        with self._config_lock:
            self._configured = False


# Global instance
_config_manager = LoggingConfigManager()


def configure_logging(
    environment: str = "development",
    level: str = "INFO",
    output_format: str = "auto",
    enable_stdlib_bridge: bool = True,
    force_reconfigure: bool = False,
) -> dict[str, Any]:
    """Configure full backend common structured logging"""
    # Validate log level
    if level.upper() not in VALID_LOG_LEVELS:
        raise ValueError(f"Invalid log level: {level}. Must be one of {VALID_LOG_LEVELS}")

    if _config_manager.is_configured() and not force_reconfigure:
        return _get_config_status(environment, output_format, enable_stdlib_bridge)

    json_format = _determine_format(environment, output_format)
    shared_processors = _build_shared_processors()
    renderer = _select_renderer(json_format)

    _configure_structlog(shared_processors)

    if enable_stdlib_bridge:
        _configure_stdlib_bridge(shared_processors, renderer, level, environment)

    _config_manager.set_configured(True)
    return {
        "configured": True,
        "format": "json" if json_format else "console",
        "processors": len(shared_processors) + 1,
        "stdlib_bridge": enable_stdlib_bridge,
    }


def _get_config_status(environment: str, output_format: str, enable_stdlib_bridge: bool) -> dict[str, Any]:
    """Get configuration status for already configured logging"""
    json_format = _determine_format(environment, output_format)
    return {
        "already_configured": True,
        "configured": True,
        "format": "json" if json_format else "console",
        "stdlib_bridge": enable_stdlib_bridge,
    }


def _determine_format(environment: str, output_format: str) -> bool:
    """Determine if JSON format should be used"""
    if output_format == "auto":
        return environment == "production"
    return output_format == "json"


def _build_shared_processors() -> list:
    """Build shared processor chain for structlog and stdlib"""
    from .processors import SerializationFallbackProcessor

    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add serialization fallback processor to handle non-serializable objects
        SerializationFallbackProcessor(),
    ]


def _select_renderer(json_format: bool):
    """Select appropriate renderer based on format"""
    if json_format:
        return structlog.processors.JSONRenderer(default=str)
    return structlog.dev.ConsoleRenderer()


def _configure_structlog(shared_processors: list) -> None:
    """Configure structlog with processors"""
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _configure_stdlib_bridge(shared_processors: list, renderer, level: str, environment: str) -> None:
    """Configure stdlib logging bridge"""
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    _configure_root_logger(formatter, level)
    _configure_uvicorn_loggers(environment)


def _configure_root_logger(formatter, level: str) -> None:
    """Configure root logger with structlog formatter"""
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper()))


def _configure_uvicorn_loggers(environment: str) -> None:
    """Configure uvicorn loggers to use structlog"""
    # Main uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True
    uvicorn_logger.setLevel(logging.INFO)

    # Access logs - verbose in development, minimal in production
    access_level = logging.INFO if environment == "development" else logging.WARNING
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = True
    uvicorn_access.setLevel(access_level)

    # Error logs - keep INFO level to capture startup/lifecycle information
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers.clear()
    uvicorn_error.propagate = True
    uvicorn_error.setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get common structured logger"""
    return structlog.get_logger(name)
