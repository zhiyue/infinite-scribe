"""Environment injection fixtures for application testing."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="function")
def app_env_redis(monkeypatch: pytest.MonkeyPatch, redis_connection_info: dict[str, str]) -> dict[str, str]:
    """
    统一把 Redis 连接信息注入到被测应用（常见 FastAPI / Flask）。
    你的应用只要从这些变量读取即可：
    - REDIS_URL 或 (REDIS_HOST/REDIS_PORT/REDIS_PASSWORD)
    """
    info = redis_connection_info
    monkeypatch.setenv("DATABASE__REDIS_HOST", info["host"])
    monkeypatch.setenv("DATABASE__REDIS_PORT", str(info["port"]))
    monkeypatch.setenv("DATABASE__REDIS_PASSWORD", info["password"])
    return {
        "REDIS_HOST": info["host"],
        "REDIS_PORT": info["port"],
        "REDIS_PASSWORD": info["password"],
    }
