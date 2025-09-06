import contextlib
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.common.events.config import build_event_type, get_domain_topic
from src.common.services.conversation_service import conversation_service
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.user import User
from src.models.workflow import EventOutbox
from src.schemas.novel.dialogue import DialogueRole, ScopeType
from testcontainers.postgres import PostgresContainer


def _build_urls(sync_url: str) -> tuple[str, str]:
    """Given a base sync url (postgresql://user:pass@host:port/db),
    return (sync_url_psycopg2, async_url_asyncpg).
    """
    # Ensure we have a sync url for alembic
    if "+" in sync_url:
        base = sync_url.split("+", 1)[1]
        sync = "postgresql+psycopg2+" + base
    else:
        sync = sync_url.replace("postgresql://", "postgresql+psycopg2://")
    async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    return sync, async_url


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_enqueue_command_persists_domain_event_and_outbox(tmp_path: Path):
    # 1) Start Postgres testcontainer
    try:
        pg = PostgresContainer("postgres:16-alpine")
        pg.start()
    except Exception as e:
        pytest.skip(f"Postgres testcontainer not available: {e}")
    try:
        base_url = pg.get_connection_url()  # postgresql://user:pass@host:port/db
        sync_url, async_url = _build_urls(base_url)

        # 2) Run alembic migrations against this DB
        cfg = AlembicConfig(str(Path("alembic.ini")))
        cfg.set_main_option("sqlalchemy.url", sync_url)
        alembic_command.upgrade(cfg, "head")

        # 3) Create async engine/sessionmaker
        engine = create_async_engine(async_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with session_factory() as db:
            # 4) Seed minimal user + novel
            user = User(username="u1", email="u1@example.com", password_hash="x")
            db.add(user)
            await db.flush()
            novel = Novel(user_id=user.id, title="t1", theme="th")
            db.add(novel)
            await db.commit()

        async with session_factory() as db:
            # 5) Create session (scope=GENESIS)
            create_res = await conversation_service.create_session(
                db, user_id=user.id, scope_type=ScopeType.GENESIS, scope_id=str(novel.id)
            )
            assert create_res["success"] is True
            session_obj = create_res["session"]
            str(getattr(session_obj, "id", session_obj["id"]))

        async with session_factory() as db:
            # 6) Enqueue Stage.Validate command (atomic: CommandInbox + DomainEvent + Outbox)
            cmd_res = await conversation_service.enqueue_command(
                db,
                user_id=user.id,
                session_id=session_obj.id if hasattr(session_obj, "id") else session_obj["id"],
                command_type="Stage.Validate",
                payload={"level": 2},
                idempotency_key=f"idem-{uuid4()}",
            )
            assert cmd_res["success"] is True
            cmd = cmd_res["command"]
            correlation_id = getattr(cmd, "id", None)

        async with session_factory() as db:
            # 7) Verify DomainEvent
            from sqlalchemy import select

            dom_event = await db.scalar(
                select(DomainEvent).where(
                    (DomainEvent.correlation_id == correlation_id)
                    & (DomainEvent.event_type == build_event_type("GENESIS", "Command.Received"))
                )
            )
            assert dom_event is not None
            # 8) Verify EventOutbox row linked by event_id
            out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_event.event_id))
            assert out is not None
            assert out.topic == get_domain_topic("GENESIS")
            assert out.payload["event_type"] == dom_event.event_type

        await engine.dispose()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_create_round_persists_round_created_and_outbox(tmp_path: Path):
    try:
        pg = PostgresContainer("postgres:16-alpine")
        pg.start()
    except Exception as e:
        pytest.skip(f"Postgres testcontainer not available: {e}")
    try:
        base_url = pg.get_connection_url()
        sync_url, async_url = _build_urls(base_url)

        cfg = AlembicConfig(str(Path("alembic.ini")))
        cfg.set_main_option("sqlalchemy.url", sync_url)
        alembic_command.upgrade(cfg, "head")

        engine = create_async_engine(async_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with session_factory() as db:
            user = User(username="u2", email="u2@example.com", password_hash="x")
            db.add(user)
            await db.flush()
            novel = Novel(user_id=user.id, title="t2", theme="th2")
            db.add(novel)
            await db.commit()

        async with session_factory() as db:
            sres = await conversation_service.create_session(
                db, user_id=user.id, scope_type=ScopeType.GENESIS, scope_id=str(novel.id)
            )
            session_obj = sres["session"]
            sid = session_obj.id if hasattr(session_obj, "id") else session_obj["id"]

        corr = str(uuid4())
        async with session_factory() as db:
            rres = await conversation_service.create_round(
                db,
                user_id=user.id,
                session_id=sid,
                role=DialogueRole.USER,
                input_data={"text": "hello"},
                model="test-model",
                correlation_id=corr,
            )
            assert rres["success"] is True

        async with session_factory() as db:
            from sqlalchemy import select

            dom_evt = await db.scalar(
                select(DomainEvent).where(
                    (DomainEvent.event_type == build_event_type("GENESIS", "Round.Created"))
                    & (DomainEvent.aggregate_id == str(sid))
                )
            )
            assert dom_evt is not None
            out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))
            assert out is not None and out.topic == get_domain_topic("GENESIS")

        await engine.dispose()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()
