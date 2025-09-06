# tests/fixtures/config.py
"""Pytest configuration and markers setup."""

from __future__ import annotations
import os
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add Redis CLI options for testcontainer configuration."""
    redis_group = parser.getgroup("redis")
    redis_group.addoption(
        "--redis-clean-strategy",
        action="store",
        choices=("prefix", "flushdb"),
        default=os.getenv("TEST_REDIS_CLEAN_STRATEGY", "prefix"),
        help="数据清理策略：prefix（推荐）或 flushdb",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests requiring external services")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
    config.addinivalue_line(
        "markers",
        "redis_integration: 需要 Redis 集成测试的用例标记（用于选择性运行）",
    )