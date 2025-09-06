from __future__ import annotations
from asyncio.events import AbstractEventLoop

import sys
import asyncio
from typing import Iterator
from asyncio import AbstractEventLoop
import pytest

USE_UVLOOP = False  # 如需性能，可改 True（并确保已安装 uvloop）

@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    if USE_UVLOOP:
        import uvloop  # pip install uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    elif sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    loop: AbstractEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        yield loop
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        if sys.version_info >= (3, 9):
            try:
                loop.run_until_complete(loop.shutdown_default_executor())
            except Exception:
                pass
        loop.close()
