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
    enable_file_logging: bool = False,
    log_file_path: str | None = None,
    file_log_format: str = "json",  # json, keyvalue, structured, compact
) -> dict[str, Any]:
    """Configure full backend common structured logging"""
    # Validate log level
    if level.upper() not in VALID_LOG_LEVELS:
        raise ValueError(f"Invalid log level: {level}. Must be one of {VALID_LOG_LEVELS}")

    # Validate file log format
    valid_file_formats = {"json", "keyvalue", "structured", "compact"}
    if file_log_format not in valid_file_formats:
        raise ValueError(f"Invalid file_log_format: {file_log_format}. Must be one of {valid_file_formats}")

    if _config_manager.is_configured() and not force_reconfigure:
        return _get_config_status(
            environment, output_format, enable_stdlib_bridge, enable_file_logging, file_log_format
        )

    json_format = _determine_format(environment, output_format)
    shared_processors = _build_shared_processors()
    renderer = _select_renderer(json_format)

    _configure_structlog(shared_processors)

    if enable_stdlib_bridge:
        _configure_stdlib_bridge(
            shared_processors, renderer, level, environment, enable_file_logging, log_file_path, file_log_format
        )

    _config_manager.set_configured(True)
    return {
        "configured": True,
        "format": "json" if json_format else "console",
        "processors": len(shared_processors) + 1,
        "stdlib_bridge": enable_stdlib_bridge,
        "file_logging": enable_file_logging,
        "file_log_format": file_log_format,
        "log_file_path": log_file_path if enable_file_logging else None,
    }


def _get_config_status(
    environment: str,
    output_format: str,
    enable_stdlib_bridge: bool,
    enable_file_logging: bool = False,
    file_log_format: str = "json",
) -> dict[str, Any]:
    """Get configuration status for already configured logging"""
    json_format = _determine_format(environment, output_format)
    return {
        "already_configured": True,
        "configured": True,
        "format": "json" if json_format else "console",
        "stdlib_bridge": enable_stdlib_bridge,
        "file_logging": enable_file_logging,
        "file_log_format": file_log_format,
    }


def _determine_format(environment: str, output_format: str) -> bool:
    """Determine if JSON format should be used"""
    if output_format == "auto":
        return environment == "production"
    return output_format == "json"


def _create_beijing_timestamper():
    """Create a timestamper that outputs Beijing time (UTC+8)"""
    import datetime
    from zoneinfo import ZoneInfo

    def beijing_timestamper(logger, method_name, event_dict):
        """Add Beijing timezone timestamp to event_dict"""
        # Get current UTC time and convert to Beijing timezone
        utc_now = datetime.datetime.now(datetime.UTC)
        beijing_time = utc_now.astimezone(ZoneInfo("Asia/Shanghai"))
        # Format: 2025-09-19 01:04:09.532 CST
        event_dict["timestamp"] = beijing_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " CST"
        return event_dict

    return beijing_timestamper


def _build_shared_processors() -> list:
    """Build shared processor chain for structlog and stdlib"""
    from .processors import SerializationFallbackProcessor

    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _create_beijing_timestamper(),  # Use Beijing timezone instead of ISO
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


def _select_file_renderer(file_log_format: str):
    """Select appropriate renderer based on file log format"""
    if file_log_format == "json":
        return structlog.processors.JSONRenderer(default=str)
    elif file_log_format == "keyvalue":
        return structlog.processors.KeyValueRenderer(
            key_order=["timestamp", "level", "event", "logger", "service", "component"]
        )
    elif file_log_format == "structured":
        # Custom structured format without colors
        return _create_structured_renderer()
    elif file_log_format == "compact":
        # Custom compact format
        return _create_compact_renderer()
    else:
        # Default to JSON for unknown formats
        return structlog.processors.JSONRenderer(default=str)


def _create_structured_renderer():
    """Create a custom structured renderer without colors"""

    def renderer(_, __, event_dict):
        timestamp = event_dict.get("timestamp", "")
        level = event_dict.get("level", "").upper()
        event = event_dict.get("event", "")
        logger = event_dict.get("logger", "")

        # Build key-value pairs for additional fields
        extra_fields = []
        for key, value in event_dict.items():
            if key not in ["timestamp", "level", "event", "logger"]:
                extra_fields.append(f"{key}={value}")

        extra_str = " " + " ".join(extra_fields) if extra_fields else ""
        return f"{timestamp} [{level}] {event} [{logger}]{extra_str}"

    return renderer


def _create_compact_renderer():
    """Create a compact renderer for brief logs"""

    def renderer(_, __, event_dict):
        # Extract time from Beijing timestamp
        timestamp = event_dict.get("timestamp", "")
        if " " in timestamp and "CST" in timestamp:
            # Format: "2025-09-19 01:06:18.435 CST" -> "01:06:18"
            date_time_part = timestamp.split(" ")[1]  # Get time part
            time_part = date_time_part.split(".")[0]  # Remove milliseconds
        else:
            time_part = timestamp

        level = event_dict.get("level", "").upper()
        event = event_dict.get("event", "")
        logger = event_dict.get("logger", "").split(".")[-1] if event_dict.get("logger") else ""

        # Include only key fields for compact format
        key_fields = []
        for key in ["command", "service", "component", "elapsed_ms"]:
            if key in event_dict:
                key_fields.append(f"{key}={event_dict[key]}")

        extra_str = f" ({', '.join(key_fields)})" if key_fields else ""
        return f"[{time_part}] {level} {event} ({logger}){extra_str}"

    return renderer


def _configure_structlog(shared_processors: list) -> None:
    """Configure structlog with processors"""
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _configure_stdlib_bridge(
    shared_processors: list,
    renderer,
    level: str,
    environment: str,
    enable_file_logging: bool = False,
    log_file_path: str | None = None,
    file_log_format: str = "json",
) -> None:
    """Configure stdlib logging bridge"""
    # Console formatter with colors
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    # File formatter based on file_log_format
    file_renderer = _select_file_renderer(file_log_format)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=file_renderer,
        foreign_pre_chain=shared_processors,
    )

    _configure_root_logger(console_formatter, file_formatter, level, enable_file_logging, log_file_path)
    _configure_uvicorn_loggers(environment)


def _configure_root_logger(
    console_formatter, file_formatter, level: str, enable_file_logging: bool = False, log_file_path: str | None = None
) -> None:
    """Configure root logger with separate formatters for console and file"""
    from datetime import datetime
    from pathlib import Path

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper()))

    # Always add console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root.addHandler(console_handler)

    # Add file handler if enabled (without colors, JSON format)
    if enable_file_logging:
        if not log_file_path:
            # Default log file path with daily rotation
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            # Generate daily log file name (one file per day)
            date_str = datetime.now().strftime("%Y%m%d")
            log_file_path = log_dir / f"is-launcher_{date_str}.log"

        # Ensure log directory exists
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setFormatter(file_formatter)  # Use the clean JSON formatter
        root.addHandler(file_handler)


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
