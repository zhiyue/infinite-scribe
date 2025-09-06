"""Integration test specific fixtures."""

from __future__ import annotations

import pytest

# 使用 PostgreSQL 的集成测试专用 fixtures

pytest_plugins = [
    "tests.integration.fixtures.config",
    "tests.integration.fixtures.redis",
    "tests.integration.fixtures.postgres",
    "tests.integration.fixtures.services",
    "tests.integration.fixtures.clients",
    "tests.integration.fixtures.app_env",
    "tests.integration.fixtures.mocks",
    "tests.integration.fixtures.asyncio_loop",
]


@pytest.fixture
async def sse_provider_override():
    """提供一个简单的 SSEProvider 覆盖示例。

    用法：
        async def test_xxx(sse_provider_override):
            # 在该测试用例作用域内，所有对默认 provider 的解析都会使用这个实例
            provider = sse_provider_override
            # 可按需预热底层服务，或做行为替换/打桩
            await provider.get_redis_sse_service()
            await provider.get_connection_manager()
            ...

    说明：
    - 该 fixture 使用 `override_provider` 上下文管理器覆盖进程级默认 provider，
      退出后会自动关闭资源并恢复。
    - FastAPI 应用若在 lifespan 中初始化了 app-scoped provider，
      路由依赖会优先使用 app.state 的 provider；此 fixture 更适用于非 Web 上下文
     （或在单测中手动禁用/绕过 lifespan 初始化的场景）。
    """
    from src.services.sse.provider import SSEProvider, override_provider

    provider = SSEProvider()
    async with override_provider(provider) as p:
        yield p
