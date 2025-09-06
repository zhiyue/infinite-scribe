from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from typing import Any, Iterator, Dict, List

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, create_engine as create_sync_engine
from testcontainers.postgres import PostgresContainer


# ---------- 1) 会话级容器 ----------
@pytest.fixture(scope="session")
def postgres_container() -> Generator[Dict[str, str], Any, None]:
    """
    启动 Postgres testcontainer 并导出连接信息（host/port/user/password/db）。
    """
    image = os.getenv("TEST_PG_IMAGE", "postgres:16-alpine")
    container = PostgresContainer(image=image)
    # 如需自定义编码/时区/参数可用 with_env / with_command
    # container = container.with_env("TZ", "UTC")

    with container as c:
        yield {
            "host": c.get_container_host_ip(),
            "port": c.get_exposed_port(5432),
            "user": c.username,
            "password": c.password,
            "database": c.dbname,
        }


# ---------- 2) 运行 Alembic 迁移（会话一次） ----------
def _build_urls(info: Dict[str, str]) -> tuple[str, str]:
    # async URL 供应用/测试使用；sync URL 供 Alembic 使用
    async_url = (
        f"postgresql+asyncpg://{info['user']}:{info['password']}"
        f"@{info['host']}:{info['port']}/{info['database']}"
    )
    sync_url = async_url.replace("+asyncpg", "")
    return async_url, sync_url


def _run_alembic_upgrade_head(sync_db_url: str) -> None:
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    # 假设项目根有 alembic.ini，脚本在 alembic/ 目录
    project_root = Path(__file__).resolve().parents[2]
    alembic_dir = project_root / "alembic"
    alembic_ini = project_root / "alembic.ini"

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(alembic_dir))
    cfg.set_main_option("sqlalchemy.url", sync_db_url)

    # 先简单验证连接
    engine = create_sync_engine(sync_db_url, future=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    engine.dispose()

    # 真实执行迁移到 head
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def migrated_database(postgres_container) -> Iterator[Dict[str, str]]:
    """
    会话开始时对空库执行 Alembic 迁移到 head。
    """
    async_url, sync_url = _build_urls(postgres_container)
    _run_alembic_upgrade_head(sync_url)
    yield {"async_url": async_url, "sync_url": sync_url}


# ---------- 3) 会话级 AsyncEngine ----------
@pytest.fixture(scope="session")
async def pg_engine(migrated_database) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        migrated_database["async_url"],
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    try:
        # 验证可用
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        yield engine
    finally:
        await engine.dispose()


# ---------- 4) 用例级会话 + 简单可靠的 TRUNCATE 隔离 ----------
@pytest.fixture
async def pg_session(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    每个用例一个 AsyncSession；用例前后 TRUNCATE 所有业务表，确保隔离。
    注意：如果你有很多表，TRUNCATE 一样很快（且事务安全）。
    """
    async_session_maker = async_sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        # 用例前清理
        await _truncate_all_tables(session)
        yield session
        # 用例后清理（双保险）
        await _truncate_all_tables(session)


async def _truncate_all_tables(session: AsyncSession) -> None:
    # 查询所有 public 模式下的业务表（排除 alembic_version）
    res = await session.execute(
        text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename <> 'alembic_version'
        """)
    )
    tables: List[str] = [r[0] for r in res.fetchall()]
    if tables:
        names = ", ".join(f'"{t}"' for t in tables)  # 引号避免大小写/关键字冲突
        # RESTART IDENTITY 重置自增；CASCADE 处理外键
        await session.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
    await session.commit()
