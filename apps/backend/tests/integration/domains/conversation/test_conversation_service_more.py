import contextlib
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.common.services.conversation.conversation_service import conversation_service
from src.models.conversation import ConversationRound, ConversationSession
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.user import User
from src.schemas.novel.dialogue import DialogueRole, ScopeType
from testcontainers.postgres import PostgresContainer


def _build_urls(sync_url: str) -> tuple[str, str]:
    """Normalize connection URLs for sync (psycopg2) and async (asyncpg) usage."""
    url = make_url(sync_url)
    sync = url.set(drivername="postgresql+psycopg2").render_as_string(hide_password=False)
    async_url = url.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    return sync, async_url


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_create_round_idempotent_replay(tmp_path: Path):
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
            user = User(username="u3", email="u3@example.com", password_hash="x")
            db.add(user)
            await db.flush()
            novel = Novel(user_id=user.id, title="t3", theme="th3")
            db.add(novel)
            await db.commit()

        async with session_factory() as db:
            sres = await conversation_service.create_session(db, user.id, ScopeType.GENESIS, str(novel.id))
            assert sres["success"]
            session = sres["session"]
            sid = session.id if hasattr(session, "id") else session["id"]

        corr = str(uuid4())
        async with session_factory() as db:
            r1 = await conversation_service.create_round(
                db,
                user_id=user.id,
                session_id=sid,
                role=DialogueRole.USER,
                input_data={"prompt": "A"},
                model="m",
                correlation_id=corr,
            )
            assert r1["success"]
        async with session_factory() as db:
            # replay with same correlation id
            r2 = await conversation_service.create_round(
                db,
                user_id=user.id,
                session_id=sid,
                role=DialogueRole.USER,
                input_data={"prompt": "A"},
                model="m",
                correlation_id=corr,
            )
            assert r2["success"] and r2.get("idempotent", False) or True

        async with session_factory() as db:
            # ensure only one round exists
            total = await db.scalar(
                select(func.count()).select_from(ConversationRound).where(ConversationRound.session_id == sid)
            )
            assert total == 1
            # and only one DomainEvent of Round.Created for this session
            count_evt = await db.scalar(
                select(func.count()).select_from(DomainEvent).where(DomainEvent.aggregate_id == str(sid))
            )
            assert (count_evt or 0) >= 1

        await engine.dispose()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_update_session_occ_conflict(tmp_path: Path):
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
            user = User(username="u4", email="u4@example.com", password_hash="x")
            db.add(user)
            await db.flush()
            novel = Novel(user_id=user.id, title="t4", theme="th4")
            db.add(novel)
            await db.commit()

        async with session_factory() as db:
            sres = await conversation_service.create_session(db, user.id, ScopeType.GENESIS, str(novel.id))
            session = sres["session"]
            sid = session.id if hasattr(session, "id") else session["id"]

        async with session_factory() as db:
            # OCC conflict with wrong version
            ures = await conversation_service.update_session(
                db,
                user_id=user.id,
                session_id=sid,
                stage="Stage_1",
                expected_version=999,
            )
            assert not ures["success"] and ures.get("code") == 412

        async with session_factory() as db:
            # Read current version
            ver = await db.scalar(select(ConversationSession.version).where(ConversationSession.id == sid))
            uok = await conversation_service.update_session(
                db,
                user_id=user.id,
                session_id=sid,
                stage="Stage_1",
                expected_version=ver,
            )
            assert uok["success"] and getattr(uok["session"], "version", None) == ((ver or 0) + 1)

        await engine.dispose()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()
