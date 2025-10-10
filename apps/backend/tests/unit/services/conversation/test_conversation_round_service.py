"""Unit tests for ConversationRoundService with modern dependency injection."""

from __future__ import annotations

from uuid import UUID, uuid4

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_round_service import ConversationRoundService
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole, ScopeType


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provide AsyncSession mock for all tests."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Conversation cache mock with explicit async helpers."""
    cache = AsyncMock()
    cache.cache_round = AsyncMock()
    cache.get_round = AsyncMock()
    return cache


@pytest.fixture
def mock_access_control() -> AsyncMock:
    """Access control mock exposing verify_session_access."""
    ctrl = AsyncMock()
    ctrl.verify_session_access = AsyncMock()
    return ctrl


@pytest.fixture
def mock_serializer() -> Mock:
    """Serializer mock returning deterministic dicts."""
    serializer = Mock()
    serializer.serialize_round = Mock()
    return serializer


# Event handler no longer used in round creation
# @pytest.fixture
# def mock_event_handler() -> AsyncMock:
#     """Event handler mock for ensuring support events."""
#     handler = AsyncMock()
#     handler.create_round_support_events = AsyncMock()
#     handler.ensure_round_events = AsyncMock()
#     return handler


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Repository mock with async methods used by services."""
    repo = AsyncMock()
    repo.list_by_session = AsyncMock()
    repo.find_by_session_and_path = AsyncMock()
    repo.find_by_correlation_id = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def round_service(
    mock_cache: AsyncMock,
    mock_access_control: AsyncMock,
    mock_serializer: Mock,
    mock_repository: AsyncMock,
) -> ConversationRoundService:
    """Create ConversationRoundService with injected dependencies."""
    return ConversationRoundService(
        cache=mock_cache,
        access_control=mock_access_control,
        serializer=mock_serializer,
        repository=mock_repository,
    )


@pytest.mark.asyncio
async def test_list_rounds_success(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
    mock_repository: AsyncMock,
    mock_serializer: Mock,
) -> None:
    """Rounds should return ORM list with serialized mirror."""
    user_id = 123
    session_id = uuid4()
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    round1 = Mock(spec=ConversationRound)
    round2 = Mock(spec=ConversationRound)
    mock_repository.list_by_session.return_value = [round1, round2]
    mock_serializer.serialize_round.side_effect = [{"round_path": "1"}, {"round_path": "2"}]

    result = await round_service.list_rounds(mock_db, user_id, session_id)

    assert result["success"] is True
    assert result["rounds"] == [round1, round2]
    assert result["serialized_rounds"] == [{"round_path": "1"}, {"round_path": "2"}]
    mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)
    mock_repository.list_by_session.assert_awaited_once_with(
        session_id=session_id,
        after=None,
        limit=50,
        order="asc",
        role=None,
    )


@pytest.mark.asyncio
async def test_list_rounds_session_not_found(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
) -> None:
    """Access failure should short-circuit list."""
    user_id = 999
    session_id = uuid4()
    mock_access_control.verify_session_access.return_value = {
        "success": False,
        "error": "Session not found",
        "code": 404,
    }

    result = await round_service.list_rounds(mock_db, user_id, session_id)

    assert result["success"] is False
    assert result["error"] == "Session not found"
    assert result["code"] == 404
    mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)


@pytest.mark.asyncio
async def test_list_rounds_access_denied(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
) -> None:
    """Access denied bubbled out directly."""
    user_id = 1
    session_id = uuid4()
    mock_access_control.verify_session_access.return_value = {
        "success": False,
        "error": "Access denied",
        "code": 403,
    }

    result = await round_service.list_rounds(mock_db, user_id, session_id)

    assert result["success"] is False
    assert result["error"] == "Access denied"
    assert result["code"] == 403
    mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)


@pytest.mark.asyncio
async def test_list_rounds_with_filters(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
    mock_repository: AsyncMock,
    mock_serializer: Mock,
) -> None:
    """Cursor + filters should hit repository accordingly."""
    user_id = 22
    session_id = uuid4()
    cursor = "5"
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    target_round = Mock(spec=ConversationRound)
    mock_repository.find_by_session_and_path.return_value = target_round
    mock_repository.list_by_session.return_value = []

    result = await round_service.list_rounds(
        mock_db,
        user_id,
        session_id,
        after=cursor,
        limit=10,
        order="desc",
        role=DialogueRole.USER,
    )

    assert result["success"] is True
    assert result["rounds"] == []
    assert result["serialized_rounds"] == []
    mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, cursor)
    mock_repository.list_by_session.assert_awaited_once_with(
        session_id=session_id,
        after=cursor,
        limit=10,
        order="desc",
        role=DialogueRole.USER,
    )


@pytest.mark.asyncio
async def test_create_round_success_new(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
    mock_cache: AsyncMock,
    mock_serializer: Mock,
    mock_repository: AsyncMock,
) -> None:
    """New round should be returned alongside serialized view and cached."""
    user_id = 321
    session_id = uuid4()
    correlation_id = str(uuid4())
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    mock_repository.find_by_correlation_id.return_value = None

    seq_result = Mock()
    seq_result.scalar_one.return_value = 3
    mock_db.execute.return_value = seq_result

    new_round = Mock(spec=ConversationRound)
    new_round.session_id = session_id
    new_round.round_path = "3"
    mock_repository.create.return_value = new_round

    serialized = {"session_id": str(session_id), "round_path": "3"}
    mock_serializer.serialize_round.return_value = serialized

    result = await round_service.create_round(
        mock_db,
        user_id,
        session_id,
        role=DialogueRole.USER,
        input_data={"prompt": "hi"},
        model="gpt-4",
        correlation_id=correlation_id,
    )

    assert result["success"] is True
    assert result["round"] == new_round
    assert result["serialized_round"] == serialized
    mock_repository.find_by_correlation_id.assert_awaited_once()
    args, _ = mock_repository.find_by_correlation_id.await_args
    assert args[0] == session_id
    assert args[1] == UUID(correlation_id)
    mock_repository.create.assert_awaited_once()
    mock_cache.cache_round.assert_awaited_once_with(str(session_id), "3", serialized)


@pytest.mark.asyncio
async def test_create_round_idempotent_replay(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
    mock_cache: AsyncMock,
    mock_serializer: Mock,
    mock_repository: AsyncMock,
) -> None:
    """Existing correlation id should reuse round and still serialize/cache."""
    user_id = 555
    session_id = uuid4()
    correlation_id = str(uuid4())
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    existing = Mock(spec=ConversationRound)
    existing.session_id = session_id
    existing.round_path = "2"
    existing.correlation_id = correlation_id
    mock_repository.find_by_correlation_id.return_value = existing
    serialized = {"session_id": str(session_id), "round_path": "2"}
    mock_serializer.serialize_round.return_value = serialized

    result = await round_service.create_round(
        mock_db,
        user_id,
        session_id,
        role=DialogueRole.USER,
        input_data={"prompt": "again"},
        model="model-x",
        correlation_id=correlation_id,
    )

    assert result["success"] is True
    assert result["round"] == existing
    assert result["serialized_round"] == serialized
    mock_repository.find_by_correlation_id.assert_awaited_once()
    mock_repository.create.assert_not_awaited()
    mock_cache.cache_round.assert_awaited_once_with(str(session_id), "2", serialized)


@pytest.mark.asyncio
async def test_create_round_session_not_found(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
) -> None:
    """Missing session should short-circuit creation."""
    mock_access_control.verify_session_access.return_value = {
        "success": False,
        "error": "Session not found",
        "code": 404,
    }

    result = await round_service.create_round(
        mock_db,
        user_id=10,
        session_id=uuid4(),
        role=DialogueRole.USER,
        input_data={},
    )

    assert result["success"] is False
    assert result["error"] == "Session not found"
    assert result["code"] == 404


@pytest.mark.asyncio
async def test_create_round_access_denied(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
) -> None:
    """Access denied propagated for create."""
    mock_access_control.verify_session_access.return_value = {
        "success": False,
        "error": "Access denied",
        "code": 403,
    }

    result = await round_service.create_round(
        mock_db,
        user_id=42,
        session_id=uuid4(),
        role=DialogueRole.USER,
        input_data={},
    )

    assert result["success"] is False
    assert result["error"] == "Access denied"
    assert result["code"] == 403


@pytest.mark.asyncio
async def test_create_round_exception(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    """Repository failures should surface internal error message."""
    session_id = uuid4()
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    seq_result = Mock()
    seq_result.scalar_one.return_value = 1
    mock_db.execute.return_value = seq_result
    mock_repository.find_by_correlation_id.return_value = None
    mock_repository.create.side_effect = Exception("db boom")

    result = await round_service.create_round(
        mock_db,
        user_id=1,
        session_id=session_id,
        role=DialogueRole.USER,
        input_data={},
    )

    assert result["success"] is False
    assert result["error"] == "Failed to create round"


@pytest.mark.asyncio
async def test_get_round_from_cache(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_cache: AsyncMock,
    mock_access_control: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    """Cache hit should bypass repository and expose cached data."""
    session_id = uuid4()
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    cached = {"session_id": str(session_id), "round_path": "5"}
    mock_cache.get_round.return_value = cached

    result = await round_service.get_round(mock_db, user_id=1, session_id=session_id, round_path="5")

    assert result["success"] is True
    assert result["round"] == cached
    assert result["serialized_round"] == cached
    assert result["cached"] is True
    mock_cache.get_round.assert_awaited_once_with(str(session_id), "5")
    mock_repository.find_by_session_and_path.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_round_from_database(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_cache: AsyncMock,
    mock_access_control: AsyncMock,
    mock_serializer: Mock,
    mock_repository: AsyncMock,
) -> None:
    """Cache miss should serialize and cache database result."""
    session_id = uuid4()
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    mock_cache.get_round.return_value = None
    db_round = Mock(spec=ConversationRound)
    db_round.session_id = session_id
    db_round.round_path = "7"
    mock_repository.find_by_session_and_path.return_value = db_round
    serialized = {"session_id": str(session_id), "round_path": "7"}
    mock_serializer.serialize_round.return_value = serialized

    result = await round_service.get_round(mock_db, user_id=9, session_id=session_id, round_path="7")

    assert result["success"] is True
    assert result["round"] == db_round
    assert result["serialized_round"] == serialized
    mock_cache.get_round.assert_awaited_once_with(str(session_id), "7")
    mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, "7")
    mock_cache.cache_round.assert_awaited_once_with(str(session_id), "7", serialized)


@pytest.mark.asyncio
async def test_get_round_not_found(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_cache: AsyncMock,
    mock_access_control: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    """Missing round should surface not found error."""
    session_id = uuid4()
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}

    mock_cache.get_round.return_value = None
    mock_repository.find_by_session_and_path.return_value = None

    result = await round_service.get_round(mock_db, user_id=4, session_id=session_id, round_path="100")

    assert result["success"] is False
    assert result["error"] == "Round not found"
    assert result["code"] == 404
    mock_cache.get_round.assert_awaited_once_with(str(session_id), "100")
    mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, "100")


@pytest.mark.asyncio
async def test_get_round_session_not_found(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
) -> None:
    """Session access failure reflected in response."""
    mock_access_control.verify_session_access.return_value = {
        "success": False,
        "error": "Session not found",
        "code": 404,
    }

    result = await round_service.get_round(mock_db, user_id=7, session_id=uuid4(), round_path="1")

    assert result["success"] is False
    assert result["error"] == "Session not found"
    assert result["code"] == 404


@pytest.mark.asyncio
async def test_get_round_access_denied(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
) -> None:
    """Access denial surfaces."""
    mock_access_control.verify_session_access.return_value = {
        "success": False,
        "error": "Access denied",
        "code": 403,
    }

    result = await round_service.get_round(mock_db, user_id=7, session_id=uuid4(), round_path="2")

    assert result["success"] is False
    assert result["error"] == "Access denied"
    assert result["code"] == 403


@pytest.mark.asyncio
async def test_get_round_database_exception(
    round_service: ConversationRoundService,
    mock_db: AsyncMock,
    mock_access_control: AsyncMock,
    mock_cache: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    """Repository error should map to internal error response."""
    session_id = uuid4()
    session = Mock(spec=ConversationSession)
    session.id = session_id
    session.scope_type = ScopeType.GENESIS.value
    session.scope_id = str(uuid4())
    mock_access_control.verify_session_access.return_value = {"success": True, "session": session}
    mock_cache.get_round.return_value = None
    mock_repository.find_by_session_and_path.side_effect = Exception("db down")

    result = await round_service.get_round(mock_db, user_id=8, session_id=session_id, round_path="1")

    assert result["success"] is False
    assert result["error"] == "Failed to get round"


def test_compute_next_round_path(round_service: ConversationRoundService) -> None:
    """Static helper should increment count string safely."""
    assert round_service._compute_next_round_path(0) == "1"
    assert round_service._compute_next_round_path(5) == "6"
    assert round_service._compute_next_round_path(999) == "1000"


def test_parse_correlation_uuid_valid(round_service: ConversationRoundService) -> None:
    """Valid UUID strings should convert to UUID objects."""
    correlation_id = str(uuid4())
    result = round_service._parse_correlation_uuid(correlation_id)
    assert isinstance(result, UUID)
    assert str(result) == correlation_id


def test_parse_correlation_uuid_invalid(round_service: ConversationRoundService) -> None:
    """Invalid UUID strings should return None without raising."""
    assert round_service._parse_correlation_uuid("invalid") is None
    assert round_service._parse_correlation_uuid(None) is None
    assert round_service._parse_correlation_uuid("") is None

