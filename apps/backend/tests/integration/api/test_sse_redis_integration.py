"""SSE + Redis 实际集成测试（使用 Testcontainers Redis）。

覆盖 Pub/Sub 实时、Streams 历史、与黑名单 TTL 行为。
使用方法：依赖 integration/conftest.py 中的可选容器开关。
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import timedelta

import pytest
from src.common.utils.datetime_utils import utc_now
from src.schemas.sse import EventScope, SSEMessage
from src.services.sse import RedisSSEService


@pytest.mark.asyncio
async def test_pubsub_realtime_event_flow(redis_service):
    """验证通过 Pub/Sub 订阅能收到 publish_event 推送的事件。"""
    # Configure global settings with testcontainer Redis
    from src.core.config import get_settings

    settings = get_settings()
    settings.database.redis_host = redis_service["host"]
    settings.database.redis_port = redis_service["port"]
    settings.database.redis_password = redis_service["password"]

    # Reconnect redis_service with new settings
    from src.db.redis import redis_service as global_redis_service

    await global_redis_service.disconnect()
    await global_redis_service.connect()

    # Use global redis_service instance which will now use testcontainer settings
    service = RedisSSEService(global_redis_service)
    await service.init_pubsub_client()

    user_id = "user-redis-integration"

    # 清理遗留 Streams 数据，避免干扰
    async with global_redis_service.acquire() as r:
        await r.delete(f"events:user:{user_id}")

    event = SSEMessage(
        event="test.event-happened",
        data={"hello": "world"},
        scope=EventScope.USER,
    )

    queue: asyncio.Queue[SSEMessage] = asyncio.Queue()

    async def _consumer():
        async for e in service.subscribe_user_events(user_id):
            await queue.put(e)
            break

    consumer_task = asyncio.create_task(_consumer())

    # 发布事件 -> 订阅端应收到
    await service.publish_event(user_id, event)

    received = await asyncio.wait_for(queue.get(), timeout=5.0)

    # 等待消费者任务自然结束或取消它
    try:
        await asyncio.wait_for(consumer_task, timeout=1.0)
    except TimeoutError:
        # 任务未在合理时间内结束，取消它
        consumer_task.cancel()
        with suppress(TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(consumer_task, timeout=2.0)

    assert received.event == event.event
    assert received.data == event.data
    assert received.scope == event.scope
    assert received.id is not None  # 来自 Streams 的实际 ID


@pytest.mark.asyncio
async def test_streams_history_returns_published_events(redis_service):
    """验证通过 Streams 可获取历史事件。"""
    # Configure global settings with testcontainer Redis
    from src.core.config import get_settings

    settings = get_settings()
    settings.database.redis_host = redis_service["host"]
    settings.database.redis_port = redis_service["port"]
    settings.database.redis_password = redis_service["password"]

    # Reconnect redis_service with new settings
    from src.db.redis import redis_service as global_redis_service

    await global_redis_service.disconnect()
    await global_redis_service.connect()

    service = RedisSSEService(global_redis_service)
    await service.init_pubsub_client()

    user_id = "user-redis-history"

    # 清理遗留数据
    async with global_redis_service.acquire() as r:
        await r.delete(f"events:user:{user_id}")

    e1 = SSEMessage(event="evt.one", data={"n": 1}, scope=EventScope.USER)
    e2 = SSEMessage(event="evt.two", data={"n": 2}, scope=EventScope.USER)
    await service.publish_event(user_id, e1)
    await service.publish_event(user_id, e2)

    # 获取历史（从头开始）
    history = await service.get_recent_events(user_id, since_id="-")

    # 至少包含刚才的两条
    kinds = [(h.event, h.data.get("n")) for h in history]
    assert ("evt.one", 1) in kinds
    assert ("evt.two", 2) in kinds


@pytest.mark.asyncio
async def test_blacklist_ttl_expiration_with_real_redis(redis_service):
    """验证黑名单键的 TTL 真实生效（过期后不再被视为黑名单）。"""
    # Configure global settings with testcontainer Redis
    from src.core.config import get_settings

    settings = get_settings()
    settings.database.redis_host = redis_service["host"]
    settings.database.redis_port = redis_service["port"]
    settings.database.redis_password = redis_service["password"]

    # Configure JWT service with testcontainer Redis
    import redis
    from src.common.services.user.auth_service import auth_service

    auth_service._redis_client = redis.Redis(
        host=redis_service["host"],
        port=redis_service["port"],
        password=redis_service["password"] or None,
        decode_responses=True,
    )

    # 造一个短期过期的时间点（1 秒）
    expires_at = utc_now() + timedelta(seconds=3)
    jti = "jti-integration-ttl"

    # 放入黑名单（使用 setex TTL）
    auth_service.blacklist_token(jti, expires_at)

    # 立刻应在黑名单内
    assert auth_service.is_token_blacklisted(jti) is True

    # 读取当前 TTL 并等待其过期
    key = f"blacklist:{jti}"
    # Use JWT service's Redis client directly for blacklist operations
    ttl = auth_service._redis_client.ttl(key)
    # ttl 可能为 -2(不存在)/-1(无过期)/>0(秒)，这里要求应为 >0
    assert isinstance(ttl, int) and ttl > 0
    await asyncio.sleep(ttl + 1)

    # 过期后不再在黑名单
    assert auth_service.is_token_blacklisted(jti) is False
