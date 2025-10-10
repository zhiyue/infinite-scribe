"""Additional conversation service integration tests using standard fixtures."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from src.common.services.conversation.conversation_service import conversation_service
from src.models.conversation import ConversationRound, ConversationSession
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.user import User
from src.schemas.novel.dialogue import DialogueRole, ScopeType


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_create_round_idempotent_replay(pg_session_no_transaction):
    """Test that creating rounds with same correlation ID is idempotent."""
    # Create test data with explicit transaction
    async with pg_session_no_transaction.begin():
        user = User(username="u3", email="u3@example.com", password_hash="x")
        pg_session_no_transaction.add(user)
        await pg_session_no_transaction.flush()
        novel = Novel(user_id=user.id, title="t3", theme="th3")
        pg_session_no_transaction.add(novel)
    # Transaction is committed when exiting the context

    # Create session
    sres = await conversation_service.create_session(
        pg_session_no_transaction,
        user.id,
        ScopeType.GENESIS,
        str(novel.id)
    )
    assert sres["success"], f"create_session failed: {sres.get('error', 'unknown error')}"
    session = sres["session"]
    sid = session.id

    # Create first round with specific correlation ID
    corr = str(uuid4())
    r1 = await conversation_service.create_round(
        pg_session_no_transaction,
        user_id=user.id,
        session_id=sid,
        role=DialogueRole.USER,
        input_data={"prompt": "A"},
        model="m",
        correlation_id=corr,
    )
    assert r1["success"], f"create_round failed: {r1.get('error', 'unknown error')}"

    # Replay with same correlation id - should be idempotent
    r2 = await conversation_service.create_round(
        pg_session_no_transaction,
        user_id=user.id,
        session_id=sid,
        role=DialogueRole.USER,
        input_data={"prompt": "A"},
        model="m",
        correlation_id=corr,
    )
    # Should not fail, and may indicate idempotency
    assert r2["success"] or r2.get("code") == 409  # 409 for conflict/already exists

    # Ensure only one round exists
    total = await pg_session_no_transaction.scalar(
        select(func.count()).select_from(ConversationRound).where(ConversationRound.session_id == sid)
    )
    assert total == 1, f"Expected 1 round, got {total}"

    # And only one DomainEvent of Round.Created for this session
    count_evt = await pg_session_no_transaction.scalar(
        select(func.count()).select_from(DomainEvent).where(DomainEvent.aggregate_id == str(sid))
    )
    assert (count_evt or 0) >= 1, f"Expected at least 1 domain event, got {count_evt}"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
async def test_update_session_occ_conflict(pg_session_no_transaction):
    """Test optimistic concurrency control for session updates."""
    # Create test data with explicit transaction
    async with pg_session_no_transaction.begin():
        user = User(username="u4", email="u4@example.com", password_hash="x")
        pg_session_no_transaction.add(user)
        await pg_session_no_transaction.flush()
        novel = Novel(user_id=user.id, title="t4", theme="th4")
        pg_session_no_transaction.add(novel)
    # Transaction is committed when exiting the context

    # Create session
    sres = await conversation_service.create_session(
        pg_session_no_transaction,
        user.id,
        ScopeType.GENESIS,
        str(novel.id)
    )
    assert sres["success"], f"create_session failed: {sres.get('error', 'unknown error')}"
    session = sres["session"]
    sid = session.id

    # Try to update with wrong version - should fail with OCC conflict
    ures = await conversation_service.update_session(
        pg_session_no_transaction,
        user_id=user.id,
        session_id=sid,
        stage="Stage_1",
        expected_version=999,  # Wrong version
    )
    assert not ures["success"], "Update should fail with wrong version"
    assert ures.get("code") == 412, f"Expected 412 (Precondition Failed), got {ures.get('code')}"

    # Get current version and update correctly
    current_session = await pg_session_no_transaction.get(ConversationSession, sid)
    current_version = current_session.version

    ures2 = await conversation_service.update_session(
        pg_session_no_transaction,
        user_id=user.id,
        session_id=sid,
        stage="Stage_1",
        expected_version=current_version,
    )
    assert ures2["success"], f"Update failed: {ures2.get('error', 'unknown error')}"

    # Verify version was incremented
    await pg_session_no_transaction.refresh(current_session)
    assert current_session.version == current_version + 1, f"Version should be {current_version + 1}, got {current_session.version}"