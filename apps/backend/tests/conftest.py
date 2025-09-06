"""Pytest configuration - thin aggregator loading fixture modules."""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# 仅负责声明要加载的本地"插件模块"（普通 py 文件）
pytest_plugins = [
    "tests.fixtures.config",
    "tests.fixtures.redis",
    "tests.fixtures.postgres",
    "tests.fixtures.services",
    "tests.fixtures.clients",
    "tests.fixtures.app_env",
    "tests.fixtures.mocks",
    "tests.fixtures.asyncio_loop",
]
