# tests/helpers/prefix_client.py
"""Redis client wrappers with key prefixes for test isolation."""

from __future__ import annotations

from typing import Any

import redis as redislib
import redis.asyncio as aioredis


class PrefixedRedis:
    """对 redis.Redis 进行 key 前缀封装，便于测试隔离。"""

    def __init__(self, client: redislib.Redis, prefix: str) -> None:
        self._c = client
        self._p = prefix

    @property
    def raw(self) -> redislib.Redis:
        """如需直接访问原生 client"""
        return self._c

    @property
    def prefix(self) -> str:
        return self._p

    # 常用操作自动加前缀
    def set(self, key: str, value: Any) -> bool:
        return bool(self._c.set(self._p + key, value))

    def get(self, key: str) -> Any:
        return self._c.get(self._p + key)

    def hset(self, name: str, key: str, value: Any) -> int:
        return int(self._c.hset(self._p + name, key, value))

    def hget(self, name: str, key: str) -> Any:
        return self._c.hget(self._p + name, key)

    def incr(self, key: str) -> int:
        return int(self._c.incr(self._p + key))

    def delete_prefixed(self) -> int:
        """删除所有带当前前缀的键"""
        keys = list(self._c.scan_iter(match=f"{self._p}*"))
        return self._c.delete(*keys) if keys else 0


class AsyncPrefixedRedis:
    """对 aioredis.Redis 进行 key 前缀封装，便于测试隔离。"""

    def __init__(self, client: aioredis.Redis, prefix: str) -> None:
        self._c = client
        self._p = prefix

    @property
    def raw(self) -> aioredis.Redis:
        """如需直接访问原生 client"""
        return self._c

    @property
    def prefix(self) -> str:
        return self._p

    # 常用异步操作都自动加前缀，避免键碰撞
    async def set(self, key: str, value: Any) -> bool:
        return bool(await self._c.set(self._p + key, value))

    async def get(self, key: str) -> Any:
        return await self._c.get(self._p + key)

    async def hset(self, name: str, key: str, value: Any) -> int:
        return int(await self._c.hset(self._p + name, key, value))

    async def hget(self, name: str, key: str) -> Any:
        return await self._c.hget(self._p + name, key)

    async def incr(self, key: str) -> int:
        return int(await self._c.incr(self._p + key))

    async def delete_prefixed(self) -> int:
        """删除所有带当前前缀的键"""
        keys = []
        async for key in self._c.scan_iter(match=f"{self._p}*"):
            keys.append(key)
        return await self._c.delete(*keys) if keys else 0
