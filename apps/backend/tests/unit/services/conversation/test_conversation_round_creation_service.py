"""Unit tests for ConversationRoundCreationService."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_round_creation_service import ConversationRoundCreationService
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole, ScopeType


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provide a mock AsyncSession."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def patch_transactional(monkeypatch):
    """Replace transactional context manager with a no-op for unit tests."""

    @asynccontextmanager
    async def _noop(_db):
        yield

    monkeypatch.setattr(
        "src.common.services.conversation.conversation_round_creation_service.transactional",
        _noop,
    )


@pytest.fixture
def service_dependencies():
    """Common service dependencies for tests."""
    cache = AsyncMock()
    access_control = AsyncMock()
    serializer = Mock()
    event_handler = AsyncMock()
    repository = AsyncMock()

    session = Mock(spec=ConversationSession)
    session.id = uuid4()
    session.scope_type = ScopeType.GENESIS.value

    access_control.verify_session_access.return_value = {"success": True, "session": session}
    repository.find_by_correlation_id.return_value = None

    round_obj = Mock(spec=ConversationRound)
    round_obj.session_id = session.id
    round_obj.round_path = "1"
    repository.create.return_value = round_obj

    serializer.serialize_round.return_value = {"round_path": round_obj.round_path}

    return {
        "cache": cache,
        "access_control": access_control,
        "serializer": serializer,
        "event_handler": event_handler,
        "repository": repository,
        "session": session,
        "round_obj": round_obj,
    }


@pytest.mark.asyncio
async def test_create_round_uses_repository_factory(mock_db, service_dependencies):
    """Service should use injected repository factory without AttributeError."""
    deps = service_dependencies
    repository = deps["repository"]

    execute_result = Mock()
    execute_result.scalar_one.return_value = 1
    mock_db.execute.return_value = execute_result

    service = ConversationRoundCreationService(
        cache=deps["cache"],
        access_control=deps["access_control"],
        serializer=deps["serializer"],
        event_handler=deps["event_handler"],
        repository_factory=lambda _db: repository,
    )

    result = await service.create_round(
        mock_db,
        user_id=123,
        session_id=deps["session"].id,
        role=DialogueRole.USER,
        input_data={"message": "hello"},
        model="model-x",
        correlation_id=None,
    )

    assert result["success"] is True
    repository.create.assert_awaited_once_with(
        session_id=deps["session"].id,
        round_path="1",
        role=DialogueRole.USER.value,
        input={"message": "hello"},
        output=None,
        model="model-x",
        correlation_id=None,
    )
    deps["event_handler"].create_round_support_events.assert_awaited_once()
    deps["cache"].cache_round.assert_awaited_once_with(
        str(deps["session"].id),
        "1",
        {"round_path": "1"},
    )


@pytest.mark.asyncio
async def test_create_branch_round_generates_child_path(mock_db, service_dependencies):
    """Branch rounds should compute child path using SQL helpers (Integer import)."""
    deps = service_dependencies
    repository = deps["repository"]

    branch_result = Mock()
    branch_result.scalar_one.return_value = 0
    mock_db.execute.return_value = branch_result

    service = ConversationRoundCreationService(
        cache=deps["cache"],
        access_control=deps["access_control"],
        serializer=deps["serializer"],
        event_handler=deps["event_handler"],
        repository_factory=lambda _db: repository,
    )

    deps["round_obj"].round_path = "1.1"
    repository.create.return_value = deps["round_obj"]
    deps["serializer"].serialize_round.return_value = {"round_path": "1.1"}

    result = await service.create_round(
        mock_db,
        user_id=123,
        session_id=deps["session"].id,
        role=DialogueRole.ASSISTANT,
        input_data={"message": "child"},
        model=None,
        correlation_id=None,
        parent_round_path="1",
    )

    assert result["success"] is True
    repository.create.assert_awaited_once_with(
        session_id=deps["session"].id,
        round_path="1.1",
        role=DialogueRole.ASSISTANT.value,
        input={"message": "child"},
        output=None,
        model=None,
        correlation_id=None,
    )
