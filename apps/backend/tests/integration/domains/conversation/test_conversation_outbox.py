from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession
from src.common.events.config import build_event_type, get_domain_topic
from src.common.services.conversation.conversation_service import conversation_service
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.user import User
from src.models.workflow import EventOutbox
from src.schemas.novel.dialogue import DialogueRole, ScopeType


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_enqueue_command_persists_domain_event_and_outbox(pg_session_no_transaction):
    # 4) Seed minimal user + novel
    # Create test data with explicit transaction to ensure it's committed before service calls
    async with pg_session_no_transaction.begin():
        user = User(username="u1", email="u1@example.com", password_hash="x")
        pg_session_no_transaction.add(user)
        await pg_session_no_transaction.flush()
        novel = Novel(user_id=user.id, title="t1", theme="th")
        pg_session_no_transaction.add(novel)
    # Transaction is committed when exiting the context

    # 5) Create session (scope=GENESIS)
    create_res = await conversation_service.create_session(
        pg_session_no_transaction, user_id=user.id, scope_type=ScopeType.GENESIS, scope_id=str(novel.id)
    )
    assert create_res["success"] is True, f"create_session failed: {create_res.get('error', 'unknown error')}"
    session_obj = create_res["session"]
    session_id = session_obj.id

    # 6) Enqueue Stage.Validate command (atomic: CommandInbox + DomainEvent + Outbox)
    cmd_res = await conversation_service.enqueue_command(
        pg_session_no_transaction,
        user_id=user.id,
        session_id=session_id,
        command_type="Stage.Validate",
        payload={"level": 2},
        idempotency_key=f"idem-{uuid4()}",
    )
    assert cmd_res["success"] is True
    cmd = cmd_res["command"]
    correlation_id = getattr(cmd, "id", None)

    # 7) Verify DomainEvent
    dom_event = await pg_session_no_transaction.scalar(
        select(DomainEvent).where(
            (DomainEvent.correlation_id == correlation_id)
            & (DomainEvent.event_type == build_event_type("GENESIS", "Command.Received"))
        )
    )
    assert dom_event is not None
    # 8) Verify EventOutbox row linked by event_id
    out = await pg_session_no_transaction.scalar(select(EventOutbox).where(EventOutbox.id == dom_event.event_id))
    assert out is not None
    assert out.topic == get_domain_topic("GENESIS")
    assert out.payload["event_type"] == dom_event.event_type


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_create_round_persists_round_created_and_outbox(pg_session_no_transaction: AsyncSession):
    # Create test data with explicit transaction to ensure it's committed before service calls
    async with pg_session_no_transaction.begin():
        user = User(username="u2", email="u2@example.com", password_hash="x")
        pg_session_no_transaction.add(user)
        await pg_session_no_transaction.flush()
        novel = Novel(user_id=user.id, title="t2", theme="th2")
        pg_session_no_transaction.add(novel)
    # Transaction is committed when exiting the context

    sres = await conversation_service.create_session(
        pg_session_no_transaction, user_id=user.id, scope_type=ScopeType.GENESIS, scope_id=str(novel.id)
    )
    session_obj = sres["session"]
    sid = session_obj.id

    corr = str(uuid4())
    rres = await conversation_service.create_round(
        pg_session_no_transaction,
        user_id=user.id,
        session_id=sid,
        role=DialogueRole.USER,
        input_data={"text": "hello"},
        model="test-model",
        correlation_id=corr,
    )
    assert rres["success"] is True, f"create_round failed: {rres.get('error', 'unknown error')}"

    dom_evt = await pg_session_no_transaction.scalar(
        select(DomainEvent).where(
            (DomainEvent.event_type == build_event_type("GENESIS", "Round.Created"))
            & (DomainEvent.aggregate_id == str(sid))
        )
    )
    assert dom_evt is not None
    out = await pg_session_no_transaction.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))
    assert out is not None and out.topic == get_domain_topic("GENESIS")
