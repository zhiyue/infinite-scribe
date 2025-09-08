from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from asyncio import AbstractEventLoop
from collections.abc import Iterator

import pytest

# 可通过环境变量切换 uvloop（默认 False）
USE_UVLOOP = os.getenv("USE_UVLOOP", "0") not in {"0", "", "false", "False"}


@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """
    提供一个会话级事件循环：
    - *nix 可选 uvloop
    - Windows 使用 Selector 策略以规避 Proactor 的部分兼容性问题
    - 会话结束：取消遗留任务 -> 关闭异步生成器 -> 关闭默认执行器 -> 关闭 loop
    """
    # 1) 事件循环策略
    if USE_UVLOOP and not sys.platform.startswith("win"):
        # uvloop 仅 *nix 可用
        import uvloop  # pip install uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    elif sys.platform.startswith("win"):
        # 避免 Proactor 某些库/子进程问题
        with contextlib.suppress(Exception):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 2) 创建并注册会话级 loop
    loop: AbstractEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        # 3) 取消所有遗留任务，防止 pending tasks 警告
        try:
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for t in pending:
                t.cancel()
            if pending:
                # 最多等待 5 秒让任务收尾
                loop.run_until_complete(asyncio.wait(pending, timeout=5))
        except RuntimeError:
            # loop 若已关闭/不可用，忽略
            pass

        # 4) 关闭异步生成器与默认执行器（Python 3.9+）
        with contextlib.suppress(RuntimeError):
            loop.run_until_complete(loop.shutdown_asyncgens())
        with contextlib.suppress(RuntimeError):
            loop.run_until_complete(loop.shutdown_default_executor())

        # 5) 关闭 loop 并清空当前全局 loop 引用
        loop.close()
        asyncio.set_event_loop(None)
