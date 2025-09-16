"""Unit tests for ConversationRoundQueryService."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_round_query_service import ConversationRoundQueryService
from src.models.conversation import ConversationRound, ConversationSession


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provide a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def service_dependencies():
    """Common dependencies for ConversationRoundQueryService tests."""
    cache = AsyncMock()
    access_control = AsyncMock()
    serializer = Mock()
    repository = AsyncMock()

    session = Mock(spec=ConversationSession)
    session.id = uuid4()

    access_control.verify_session_access.return_value = {"success": True, "session": session}

    round_obj = Mock(spec=ConversationRound)
    round_obj.session_id = session.id
    round_obj.round_path = "2"
    repository.find_by_session_and_path.return_value = round_obj
    repository.list_by_session.return_value = [round_obj]

    serializer.serialize_round.side_effect = lambda r: {"round_path": r.round_path}

    return {
        "cache": cache,
        "access_control": access_control,
        "serializer": serializer,
        "repository": repository,
        "session": session,
        "round_obj": round_obj,
    }


@pytest.mark.asyncio
async def test_list_rounds_preserves_round_path_cursor(mock_db, service_dependencies):
    """Round-path cursor should be forwarded without conversion."""
    deps = service_dependencies
    service = ConversationRoundQueryService(
        cache=deps["cache"],
        access_control=deps["access_control"],
        serializer=deps["serializer"],
        repository_factory=lambda _db: deps["repository"],
    )

    after_cursor = "2"
    result = await service.list_rounds(
        mock_db,
        user_id=123,
        session_id=deps["session"].id,
        after=after_cursor,
    )

    assert result["success"] is True
    deps["repository"].list_by_session.assert_awaited_once_with(
        session_id=deps["session"].id,
        after=after_cursor,
        limit=50,
        order="asc",
        role=None,
    )


@pytest.mark.asyncio
async def test_list_rounds_invalid_cursor_resets_to_none(mock_db, service_dependencies):
    """Invalid round-path cursor should be ignored."""
    deps = service_dependencies
    deps["repository"].find_by_session_and_path.return_value = None

    service = ConversationRoundQueryService(
        cache=deps["cache"],
        access_control=deps["access_control"],
        serializer=deps["serializer"],
        repository_factory=lambda _db: deps["repository"],
    )

    await service.list_rounds(
        mock_db,
        user_id=123,
        session_id=deps["session"].id,
        after="99",
    )

    deps["repository"].list_by_session.assert_awaited_once_with(
        session_id=deps["session"].id,
        after=None,
        limit=50,
        order="asc",
        role=None,
    )
