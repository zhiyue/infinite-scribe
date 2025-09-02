"""Tests for core logging configuration module"""

import logging

import structlog
from src.core.logging.config import configure_logging, get_logger


class TestLoggingConfiguration:
    """Test logging configuration functionality"""

    def setup_method(self):
        """Setup for each test method"""
        # Reset structlog configuration before each test
        structlog.reset_defaults()

    def test_configure_logging_development(self):
        """Test development environment logging configuration"""
        # Execute
        config = configure_logging(
            environment="development", level="DEBUG", output_format="console", enable_stdlib_bridge=True
        )

        # Assert
        assert config["configured"] is True
        logger = get_logger("test_component")
        assert hasattr(logger, "info")
        assert hasattr(logger, "bind")

    def test_configure_logging_production(self):
        """Test production environment logging configuration (JSON format)"""
        # Execute
        config = configure_logging(
            environment="production", level="INFO", output_format="json", enable_stdlib_bridge=True
        )

        # Assert
        assert config["configured"] is True
        assert config["format"] == "json"

        logger = get_logger("api_adapter")
        assert logger is not None

        # Test context binding
        bound_logger = logger.bind(component="api", service="api-gateway", state="starting")
        assert bound_logger is not None

    def test_stdlib_bridge(self):
        """Test stdlib to structlog bridge"""
        # Execute
        configure_logging(environment="development", enable_stdlib_bridge=True)

        # Use standard library logger
        stdlib_logger = logging.getLogger("test.stdlib")

        # Should not raise an error (logging gets processed by structlog)
        stdlib_logger.info("This should be handled by structlog")

        # Test that logger exists
        assert stdlib_logger is not None

    def test_idempotent_configuration(self):
        """Test idempotent configuration"""
        # Execute
        config1 = configure_logging(environment="development")
        config2 = configure_logging(environment="development")  # Duplicate configuration

        # Assert
        assert config1["configured"] is True
        assert config2["already_configured"] is True  # Idempotent flag

    def test_force_reconfigure(self):
        """Test forced reconfiguration (recommended for unit tests)"""
        # Setup: configure once
        configure_logging(environment="development")

        # Execute: forced reconfiguration (unit test recommended usage)
        config = configure_logging(
            environment="production",
            force_reconfigure=True,  # Avoid pytest multi-entry init order issues
        )

        # Assert
        assert config["configured"] is True
        assert "already_configured" not in config

    def test_auto_format_selection(self):
        """Test automatic format selection based on environment"""
        # Test development environment
        dev_config = configure_logging(environment="development", output_format="auto", force_reconfigure=True)
        assert dev_config["format"] == "console"

        # Test production environment
        prod_config = configure_logging(environment="production", output_format="auto", force_reconfigure=True)
        assert prod_config["format"] == "json"

    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a bound logger instance"""
        configure_logging(force_reconfigure=True)

        logger = get_logger("test_component")

        assert logger is not None
        assert hasattr(logger, "bind")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    def teardown_method(self):
        """Cleanup after each test method"""
        # Reset structlog to defaults
        structlog.reset_defaults()
