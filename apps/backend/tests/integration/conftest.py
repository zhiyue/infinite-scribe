"""Integration test specific fixtures."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 PostgreSQL 的集成测试专用 fixtures


@pytest.fixture
async def db_session(postgres_test_session) -> AsyncSession:
    """提供 PostgreSQL 数据库会话用于集成测试，并在每个测试后清理数据。"""
    # 在测试开始前清理数据库
    await postgres_test_session.execute(text("TRUNCATE TABLE users, sessions, email_verifications, domain_events CASCADE"))
    await postgres_test_session.commit()

    # 提供会话给测试
    yield postgres_test_session

    # 测试后再次清理（可选，但有助于确保隔离）
    await postgres_test_session.execute(text("TRUNCATE TABLE users, sessions, email_verifications, domain_events CASCADE"))
    await postgres_test_session.commit()


@pytest.fixture
async def client(postgres_async_client) -> AsyncClient:
    """提供使用 PostgreSQL 的异步客户端用于集成测试。"""
    # 直接使用已经配置好的 postgres_async_client
    yield postgres_async_client
