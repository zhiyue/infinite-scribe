from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.api.main import app as fastapi_app
from src.database import get_db as api_get_db
from src.middleware.auth import require_auth as api_require_auth
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.user import User
from src.models.workflow import EventOutbox
from testcontainers.postgres import PostgresContainer


def _build_urls(base_url: str) -> tuple[str, str]:
    """Convert a base postgresql URL to sync (psycopg2) and async (asyncpg) URLs."""
    # Handle different input formats
    if "postgresql+psycopg2://" in base_url:
        # Already psycopg2, create asyncpg version
        sync_url = base_url
        async_url = base_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif "postgresql+asyncpg://" in base_url:
        # Already asyncpg, create psycopg2 version
        async_url = base_url
        sync_url = base_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    else:
        # Plain postgresql://, create both versions
        sync_url = base_url.replace("postgresql://", "postgresql+psycopg2://")
        async_url = base_url.replace("postgresql://", "postgresql+asyncpg://")
    
    return sync_url, async_url


@asynccontextmanager
async def override_db_dep(session_maker: async_sessionmaker[AsyncSession]):
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_maker() as s:
            try:
                yield s
            finally:
                await s.close()

    fastapi_app.dependency_overrides[api_get_db] = _override_get_db
    try:
        yield
    finally:
        fastapi_app.dependency_overrides.pop(api_get_db, None)


@asynccontextmanager
async def override_auth_dep(user: User):
    async def _override_require_auth() -> User:
        return user

    fastapi_app.dependency_overrides[api_require_auth] = _override_require_auth
    try:
        yield
    finally:
        fastapi_app.dependency_overrides.pop(api_require_auth, None)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_conversations_api_endpoints_flow(tmp_path: Path):
    # 1) Start Postgres
    try:
        pg = PostgresContainer("postgres:16-alpine")
        pg.start()
    except Exception as e:
        pytest.skip(f"Postgres testcontainer not available: {e}")
    try:
        base_url = pg.get_connection_url()
        sync_url, async_url = _build_urls(base_url)

        # 2) Migrate
        cfg = AlembicConfig(str(Path("alembic.ini")))
        cfg.set_main_option("sqlalchemy.url", sync_url)
        alembic_command.upgrade(cfg, "head")

        # 3) Engine + Session
        engine = create_async_engine(async_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        # 4) Seed user/novel
        async with session_factory() as db:
            user = User(username="apiu", email="apiu@example.com", password_hash="x", is_verified=True)
            db.add(user)
            await db.flush()
            novel = Novel(user_id=user.id, title="apinv", theme="api")
            db.add(novel)
            await db.commit()

        # 5) Override get_db & require_auth; Stub out lifespan external services via monkeypatch at import level
        # We bypass lifespan heavy deps by not starting the app lifespan in test client (httpx's ASGITransport does not run lifespan by default)
        async with override_db_dep(session_factory), override_auth_dep(user):
            async with AsyncClient(transport=None, base_url="http://testserver") as _:
                pass  # noop to satisfy type checker
            # Use httpx>=0.24's ASGITransport to avoid lifespan
            from httpx import ASGITransport

            async with AsyncClient(
                transport=ASGITransport(app=fastapi_app, lifespan="off"), base_url="http://testserver"
            ) as client:
                # Create session
                resp = await client.post(
                    "/api/v1/conversations/sessions",
                    json={"scope_type": "GENESIS", "scope_id": str(novel.id)},
                    headers={"X-Correlation-Id": "corr-api-1"},
                )
                assert resp.status_code == 201
                data = resp.json()["data"]
                session_id = data["id"]
                assert resp.headers.get("ETag") is not None

                # Enqueue Stage.Validate command via API
                resp2 = await client.post(
                    f"/api/v1/conversations/sessions/{session_id}/commands",
                    json={"type": "Stage.Validate", "payload": {"level": 2}},
                    headers={"Idempotency-Key": f"idem-{uuid4()}"},
                )
                assert resp2.status_code == 202
                assert "Location" in resp2.headers

                # Create round via API
                resp3 = await client.post(
                    f"/api/v1/conversations/sessions/{session_id}/rounds",
                    json={"role": "user", "input": {"msg": "hi"}, "model": "m1", "correlation_id": str(uuid4())},
                )
                assert resp3.status_code in (200, 201)

        # 6) Validate DomainEvent + Outbox exist for both operations
        async with session_factory() as db:
            # Command.Received exists
            from sqlalchemy import select

            evt_cmd = await db.scalar(
                select(DomainEvent).where(DomainEvent.event_type == "Genesis.Session.Command.Received")
            )
            assert evt_cmd is not None
            out_cmd = await db.scalar(select(EventOutbox).where(EventOutbox.id == evt_cmd.event_id))
            assert out_cmd is not None and out_cmd.payload["event_type"] == evt_cmd.event_type

            # Round.Created exists
            evt_round = await db.scalar(
                select(DomainEvent).where(DomainEvent.event_type == "Genesis.Session.Round.Created")
            )
            assert evt_round is not None
            out_round = await db.scalar(select(EventOutbox).where(EventOutbox.id == evt_round.event_id))
            assert out_round is not None

        await engine.dispose()
    finally:
        with suppress(Exception):
            pg.stop()
