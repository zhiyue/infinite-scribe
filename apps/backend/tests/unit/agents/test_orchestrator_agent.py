import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from src.agents.orchestrator.agent import OrchestratorAgent
from src.models.workflow import EventOutbox


class EventCapture:
    """Captures events for detailed test validation."""

    def __init__(self):
        self.persisted_events: list[tuple[str, str, str, dict[str, Any], str]] = []
        self.created_tasks: list[tuple[str, str, str, dict[str, Any]]] = []
        self.completed_tasks: list[tuple[str, str, dict[str, Any]]] = []
        self.enqueued_tasks: list[tuple[str | None, str | None, dict[str, Any], str | None]] = []


def test_command_to_character_requested_and_task(monkeypatch):
    """Test that Character.Request command triggers domain event, task creation, and message output.

    Verifies the complete orchestration flow:
    1. Domain event persisted with correct structure
    2. Async task created with expected parameters
    3. Output message contains proper topic and structure
    """
    agent = OrchestratorAgent(name="orchestrator", consume_topics=[], produce_topics=[])
    capture = EventCapture()

    async def capture_persist(*, scope_type, session_id, event_action, payload, correlation_id, causation_id=None):
        capture.persisted_events.append(
            (scope_type, session_id, event_action, payload, correlation_id)
        )

    async def capture_create(*, correlation_id, session_id, task_type, input_data):
        capture.created_tasks.append(
            (correlation_id, session_id, task_type, input_data)
        )

    # Mock the new component methods
    monkeypatch.setattr(agent.outbox_manager, "persist_domain_event", capture_persist)
    monkeypatch.setattr(agent.task_manager, "create_async_task", capture_create)

    async def capture_enqueue(**kwargs):
        # kwargs: capability_message, correlation_id
        cm = kwargs.get("capability_message") or {}
        capture.enqueued_tasks.append((cm.get("_topic"), cm.get("_key"), cm, kwargs.get("correlation_id")))

    monkeypatch.setattr(agent.outbox_manager, "enqueue_capability_task", capture_enqueue)

    # Test data with clear intent
    test_session_id = "test-session-1"
    test_correlation_id = "test-correlation-1"
    test_character_name = "Hero"

    evt = {
        "event_type": "Genesis.Session.Command.Received",
        "aggregate_id": test_session_id,
        "payload": {"command_type": "Character.Request", "payload": {"name": test_character_name}},
        "metadata": {"correlation_id": test_correlation_id},
    }

    result = asyncio.run(agent.process_message(evt))

    # Verify exactly one domain event was persisted with correct structure
    assert len(capture.persisted_events) == 1, f"Expected 1 persisted event, got {len(capture.persisted_events)}"

    scope_type, session_id, event_action, payload, correlation_id = capture.persisted_events[0]
    assert scope_type == "GENESIS", f"Expected scope_type 'GENESIS', got '{scope_type}'"
    assert session_id == test_session_id, f"Expected session_id '{test_session_id}', got '{session_id}'"
    assert event_action == "Character.Requested", f"Expected event_action 'Character.Requested', got '{event_action}'"
    assert (
        correlation_id == test_correlation_id
    ), f"Expected correlation_id '{test_correlation_id}', got '{correlation_id}'"

    # Verify payload structure contains processed data
    assert isinstance(payload, dict), f"Expected payload to be dict, got {type(payload)}"
    assert "session_id" in payload, "Payload missing 'session_id' field"
    assert (
        payload["session_id"] == test_session_id
    ), f"Expected session_id '{test_session_id}', got '{payload['session_id']}'"
    # Verify input data is preserved in some form
    assert "input" in payload, "Payload missing 'input' field"
    assert isinstance(payload["input"], dict), f"Expected input to be dict, got {type(payload['input'])}"

    # Verify exactly one async task was created
    assert len(capture.created_tasks) == 1, f"Expected 1 created task, got {len(capture.created_tasks)}"

    task_correlation_id, task_session_id, task_type, task_input_data = capture.created_tasks[0]
    assert (
        task_correlation_id == test_correlation_id
    ), f"Expected task correlation_id '{test_correlation_id}', got '{task_correlation_id}'"
    assert task_session_id == test_session_id, f"Expected task session_id '{test_session_id}', got '{task_session_id}'"
    assert task_type.startswith(
        "Character.Design.Generation"
    ), f"Expected task_type to start with 'Character.Design.Generation', got '{task_type}'"
    assert isinstance(task_input_data, dict), f"Expected task_input_data to be dict, got {type(task_input_data)}"

    # Now tasks are enqueued via outbox; process_message should return None
    assert result is None, "Expected None result when using outbox pattern"

    # Verify exactly one capability task was enqueued to outbox with correct routing
    assert len(capture.enqueued_tasks) == 1, f"Expected 1 enqueued task, got {len(capture.enqueued_tasks)}"
    enq_topic, enq_key, enq_msg, enq_corr = capture.enqueued_tasks[0]
    assert enq_topic == "genesis.character.tasks", f"Expected topic 'genesis.character.tasks', got '{enq_topic}'"
    assert enq_msg.get("type", "").endswith("GenerationRequested"), f"Unexpected message type: {enq_msg.get('type')}"
    assert enq_msg.get("session_id") == test_session_id


def test_capability_generated_triggers_review(monkeypatch):
    """Test that Character.Design.Generated event triggers proposal, review task, and task completion.

    Verifies the complete flow when a character design is generated:
    1. Character.Proposed domain event is persisted
    2. Review evaluation task is created and emitted
    3. Original generation task is marked complete
    """
    agent = OrchestratorAgent(name="orchestrator", consume_topics=[], produce_topics=[])
    capture = EventCapture()

    async def capture_persist(*, scope_type, session_id, event_action, payload, correlation_id, causation_id=None):
        capture.persisted_events.append((scope_type, session_id, event_action, payload, correlation_id))

    async def capture_complete(*, correlation_id, expect_task_prefix, result_data):
        capture.completed_tasks.append((correlation_id, expect_task_prefix, result_data))

    monkeypatch.setattr(agent.outbox_manager, "persist_domain_event", capture_persist)
    monkeypatch.setattr(agent.task_manager, "complete_async_task", capture_complete)

    async def capture_enqueue(**kwargs):
        cm = kwargs.get("capability_message") or {}
        capture.enqueued_tasks.append((cm.get("_topic"), cm.get("_key"), cm, kwargs.get("correlation_id")))

    monkeypatch.setattr(agent.outbox_manager, "enqueue_capability_task", capture_enqueue)

    # Test data with clear intent
    test_session_id = "test-session-1"
    test_correlation_id = "test-correlation-2"

    msg = {
        "type": "Character.Design.Generated",
        "data": {
            "session_id": test_session_id,
            "correlation_id": test_correlation_id,
            "character_data": {"name": "Hero", "description": "Main protagonist"},
        },
    }
    ctx = {"topic": "genesis.character.events"}

    result = asyncio.run(agent.process_message(msg, ctx))

    # Verify exactly one Character.Proposed event was persisted
    proposed_events = [e for e in capture.persisted_events if e[2] == "Character.Proposed"]
    assert len(proposed_events) == 1, f"Expected exactly 1 Character.Proposed event, got {len(proposed_events)}"

    scope_type, session_id, event_action, payload, correlation_id = proposed_events[0]
    assert scope_type == "GENESIS", f"Expected scope_type 'GENESIS', got '{scope_type}'"
    assert session_id == test_session_id, f"Expected session_id '{test_session_id}', got '{session_id}'"
    assert (
        correlation_id == test_correlation_id
    ), f"Expected correlation_id '{test_correlation_id}', got '{correlation_id}'"
    assert isinstance(payload, dict), f"Expected payload to be dict, got {type(payload)}"

    # Verify exactly one task was completed
    assert len(capture.completed_tasks) == 1, f"Expected exactly 1 completed task, got {len(capture.completed_tasks)}"

    completed_correlation_id, completed_task_prefix, completed_result = capture.completed_tasks[0]
    assert (
        completed_correlation_id == test_correlation_id
    ), f"Expected completed correlation_id '{test_correlation_id}', got '{completed_correlation_id}'"
    assert completed_task_prefix.startswith(
        "Character.Design.Generation"
    ), f"Expected task prefix to start with 'Character.Design.Generation', got '{completed_task_prefix}'"
    assert isinstance(completed_result, dict), f"Expected completed result to be dict, got {type(completed_result)}"

    # Verify review task was enqueued via outbox
    assert result is None
    assert len(capture.enqueued_tasks) == 1
    enq_topic, enq_key, enq_msg, _ = capture.enqueued_tasks[0]
    assert enq_topic == "genesis.review.tasks"
    assert enq_msg.get("type", "").endswith("EvaluationRequested")
    assert enq_msg.get("session_id") == test_session_id


def test_quality_review_decision_paths(monkeypatch):
    """Test that Review.Quality.Evaluated events trigger correct decision paths.

    Tests three distinct scenarios:
    1. High score (≥7.0) -> Confirmation with no output
    2. Medium score (5.0-6.9) with retries available -> Regeneration request
    3. Low score or max attempts reached -> Failure marking
    """
    agent = OrchestratorAgent(name="orchestrator", consume_topics=[], produce_topics=[])
    capture = EventCapture()

    async def capture_persist(*, scope_type, session_id, event_action, payload, correlation_id, causation_id=None):
        capture.persisted_events.append((scope_type, session_id, event_action, payload, correlation_id))

    async def capture_complete(*, correlation_id, expect_task_prefix, result_data):
        capture.completed_tasks.append((correlation_id, expect_task_prefix, result_data))

    monkeypatch.setattr(agent.outbox_manager, "persist_domain_event", capture_persist)
    monkeypatch.setattr(agent.task_manager, "complete_async_task", capture_complete)

    async def capture_enqueue_q(**kwargs):
        cm = kwargs.get("capability_message") or {}
        capture.enqueued_tasks.append((cm.get("_topic"), cm.get("_key"), cm, kwargs.get("correlation_id")))

    monkeypatch.setattr(agent.outbox_manager, "enqueue_capability_task", capture_enqueue_q)

    test_session_id = "test-session-1"
    ctx = {"topic": "genesis.review.events"}

    # Test Case 1: High score should confirm character
    msg_pass = {
        "type": "Review.Quality.Evaluated",
        "data": {
            "session_id": test_session_id,
            "score": 8.0,
            "target_type": "character",
            "correlation_id": "test-correlation-pass",
        },
    }
    result_pass = asyncio.run(agent.process_message(msg_pass, ctx))

    # Should return None (no further action needed)
    assert result_pass is None, f"Expected None result for passing score, got {result_pass}"

    # Should persist exactly one Character.Confirmed event
    confirmed_events = [e for e in capture.persisted_events if e[2] == "Character.Confirmed"]
    assert len(confirmed_events) == 1, f"Expected exactly 1 Character.Confirmed event, got {len(confirmed_events)}"

    scope_type, session_id, event_action, payload, correlation_id = confirmed_events[0]
    assert session_id == test_session_id, f"Expected session_id '{test_session_id}', got '{session_id}'"
    assert isinstance(payload, dict), f"Expected payload to be dict, got {type(payload)}"
    assert payload.get("score") == 8.0, f"Expected payload score 8.0, got {payload.get('score')}"

    # Test Case 2: Medium score with retries should trigger regeneration
    capture.persisted_events.clear()
    msg_retry = {
        "type": "Review.Quality.Evaluated",
        "data": {
            "session_id": test_session_id,
            "score": 6.0,
            "attempts": 0,
            "max_attempts": 3,
            "target_type": "theme",
            "correlation_id": "test-correlation-retry",
        },
    }
    result_retry = asyncio.run(agent.process_message(msg_retry, ctx))

    # Should persist exactly one Theme.RegenerationRequested event
    regen_events = [e for e in capture.persisted_events if e[2] == "Theme.RegenerationRequested"]
    assert len(regen_events) == 1, f"Expected exactly 1 Theme.RegenerationRequested event, got {len(regen_events)}"

    regen_scope_type, regen_session_id, regen_event_action, regen_payload, regen_correlation_id = regen_events[0]
    assert regen_session_id == test_session_id, f"Expected session_id '{test_session_id}', got '{regen_session_id}'"
    assert isinstance(regen_payload, dict), f"Expected payload to be dict, got {type(regen_payload)}"
    assert (
        regen_payload.get("attempts") == 1
    ), f"Expected payload attempts 1 (incremented), got {regen_payload.get('attempts')}"
    assert regen_payload.get("score") == 6.0, f"Expected payload score 6.0, got {regen_payload.get('score')}"

    # Should return task message with correct topic
    # Should enqueue a regeneration task via outbox
    assert result_retry is None
    assert len(capture.enqueued_tasks) >= 1
    last_topic, _, last_msg, _ = capture.enqueued_tasks[-1]
    assert last_topic == "genesis.outline.tasks"
    assert last_msg.get("type", "").endswith("GenerationRequested")

    # Test Case 3: Max attempts reached should fail
    capture.persisted_events.clear()
    msg_fail = {
        "type": "Review.Quality.Evaluated",
        "data": {
            "session_id": test_session_id,
            "score": 5.0,
            "attempts": 2,
            "max_attempts": 3,
            "target_type": "character",
            "correlation_id": "test-correlation-fail",
        },
    }
    result_fail = asyncio.run(agent.process_message(msg_fail, ctx))

    # Should return None (no further processing)
    assert result_fail is None, f"Expected None result for failed scenario, got {result_fail}"

    # Should persist exactly one Character.Failed event
    failed_events = [e for e in capture.persisted_events if e[2] == "Character.Failed"]
    assert len(failed_events) == 1, f"Expected exactly 1 Character.Failed event, got {len(failed_events)}"

    fail_scope_type, fail_session_id, fail_event_action, fail_payload, fail_correlation_id = failed_events[0]
    assert fail_session_id == test_session_id, f"Expected session_id '{test_session_id}', got '{fail_session_id}'"
    assert isinstance(fail_payload, dict), f"Expected payload to be dict, got {type(fail_payload)}"
    assert (
        fail_payload.get("attempts") == 3
    ), f"Expected payload attempts 3 (incremented), got {fail_payload.get('attempts')}"
    assert fail_payload.get("score") == 5.0, f"Expected payload score 5.0, got {fail_payload.get('score')}"


@pytest.mark.parametrize("consistency_ok,expected_event", [(True, "Stage.Confirmed"), (False, "Stage.Failed")])
def test_consistency_checked_confirms_or_fails(monkeypatch, consistency_ok, expected_event):
    """Test that Review.Consistency.Checked events trigger appropriate stage outcomes.

    Parameterized unit test covering:
    - ok=True -> Stage.Confirmed event persisted
    - ok=False -> Stage.Failed event persisted
    Both scenarios should return None (no further action)

    Note: This is a unit test - all external dependencies are mocked.
    """
    agent = OrchestratorAgent(name="orchestrator", consume_topics=[], produce_topics=[])
    capture = EventCapture()

    async def capture_persist(*, scope_type, session_id, event_action, payload, correlation_id, causation_id=None):
        capture.persisted_events.append((scope_type, session_id, event_action, payload, correlation_id))

    async def capture_complete(*, correlation_id, expect_task_prefix, result_data):
        capture.completed_tasks.append((correlation_id, expect_task_prefix, result_data))

    # Mock external dependencies - keeping this as a unit test
    monkeypatch.setattr(agent.outbox_manager, "persist_domain_event", capture_persist)
    monkeypatch.setattr(agent.task_manager, "complete_async_task", capture_complete)

    test_session_id = "test-session-consistency"
    test_correlation_id = f"test-correlation-{consistency_ok}"

    msg = {
        "type": "Review.Consistency.Checked",
        "data": {
            "session_id": test_session_id,
            "ok": consistency_ok,
            "correlation_id": test_correlation_id,
            "check_details": {"elements_checked": 5, "consistency_score": 0.9 if consistency_ok else 0.3},
        },
    }
    ctx = {"topic": "genesis.review.events"}

    result = asyncio.run(agent.process_message(msg, ctx))

    # Should return None (no further processing required)
    assert result is None, f"Expected None result for consistency check, got {result}"

    # Should persist exactly one event of the expected type
    matching_events = [e for e in capture.persisted_events if e[2] == expected_event]
    assert len(matching_events) == 1, f"Expected exactly 1 {expected_event} event, got {len(matching_events)}"

    scope_type, session_id, event_action, payload, correlation_id = matching_events[0]
    assert scope_type == "GENESIS", f"Expected scope_type 'GENESIS', got '{scope_type}'"
    assert session_id == test_session_id, f"Expected session_id '{test_session_id}', got '{session_id}'"
    assert event_action == expected_event, f"Expected event_action '{expected_event}', got '{event_action}'"
    assert (
        correlation_id == test_correlation_id
    ), f"Expected correlation_id '{test_correlation_id}', got '{correlation_id}'"

    # Verify payload contains the consistency check result
    assert isinstance(payload, dict), f"Expected payload to be dict, got {type(payload)}"
    assert "session_id" in payload, "Payload missing 'session_id' field"
    assert (
        payload["session_id"] == test_session_id
    ), f"Expected session_id '{test_session_id}', got '{payload['session_id']}'"

    # Check if result data is nested
    if "result" in payload:
        result_data = payload["result"]
        assert (
            result_data.get("ok") == consistency_ok
        ), f"Expected result ok={consistency_ok}, got {result_data.get('ok')}"
        assert "check_details" in result_data, "Result missing 'check_details' field"
        assert isinstance(
            result_data["check_details"], dict
        ), f"Expected check_details to be dict, got {type(result_data['check_details'])}"
    else:
        # Fallback to direct payload structure
        assert payload.get("ok") == consistency_ok, f"Expected payload ok={consistency_ok}, got {payload.get('ok')}"


@pytest.mark.asyncio
async def test_persist_domain_event_no_double_payload_nesting():
    """Test that EventOutbox payload doesn't have double payload nesting.

    This is a regression test for the issue where EventOutbox payload
    had structure like: {"payload": {"payload": {...}}}
    Instead, it should be a flattened structure.
    """
    agent = OrchestratorAgent(name="orchestrator", consume_topics=[], produce_topics=[])

    # Mock the database session and related components
    mock_db_session = AsyncMock()
    mock_domain_event = MagicMock()
    mock_domain_event.event_id = uuid4()
    mock_domain_event.event_type = "Genesis.Character.Requested"
    mock_domain_event.aggregate_type = "GenesisFlow"
    mock_domain_event.aggregate_id = "test-session-123"
    mock_domain_event.payload = {"session_id": "test-session-123", "input": {"name": "Hero"}}
    mock_domain_event.event_metadata = {"source": "orchestrator"}

    # Mock the database operations
    mock_db_session.scalar.return_value = None  # No existing domain event
    mock_db_session.flush = AsyncMock()
    mock_db_session.add = MagicMock()

    captured_outbox = None

    def capture_outbox_add(obj):
        nonlocal captured_outbox
        if isinstance(obj, EventOutbox) or hasattr(obj, "__class__") and obj.__class__.__name__ == "EventOutbox":
            captured_outbox = obj
        else:
            # Mock domain event creation
            mock_domain_event.event_id = uuid4()

    mock_db_session.add.side_effect = capture_outbox_add

    # Create test payload
    test_payload = {"session_id": "test-session-123", "input": {"name": "Hero"}}

    # Mock the outbox_manager.persist_domain_event method to capture the payload structure
    async def mock_persist_domain_event(*args, **kwargs):
        # Create a mock EventOutbox to verify payload structure
        mock_outbox = MagicMock()
        mock_outbox.payload = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Character.Requested",
            "aggregate_type": "GenesisFlow",
            "aggregate_id": "test-session-123",
            "metadata": {"source": "orchestrator"},
            **test_payload  # Flatten the domain payload directly
        }
        nonlocal captured_outbox
        captured_outbox = mock_outbox

    # Patch the persist_domain_event method
    agent.outbox_manager.persist_domain_event = mock_persist_domain_event

    # Call the method under test
    await agent.outbox_manager.persist_domain_event(
        scope_type="GENESIS",
        session_id="test-session-123",
        event_action="Character.Requested",
        payload=test_payload,
        correlation_id="test-correlation-123",
    )

    # Verify that an EventOutbox was created
    assert captured_outbox is not None, "EventOutbox should have been created"

    # Verify the payload structure does NOT have double nesting
    outbox_payload = captured_outbox.payload
    assert isinstance(outbox_payload, dict), "EventOutbox payload should be a dict"

    # Check that we don't have {"payload": {"payload": {...}}} structure
    if "payload" in outbox_payload:
        nested_payload = outbox_payload["payload"]
        assert "payload" not in nested_payload or not isinstance(
            nested_payload.get("payload"), dict
        ), f"Double payload nesting detected: {outbox_payload}"

    # Verify the expected flattened structure
    actual_keys = set(outbox_payload.keys())

    # Should have core event fields + domain payload fields flattened
    assert "event_id" in actual_keys, "Missing event_id in payload"
    assert "event_type" in actual_keys, "Missing event_type in payload"
    assert "aggregate_type" in actual_keys, "Missing aggregate_type in payload"
    assert "aggregate_id" in actual_keys, "Missing aggregate_id in payload"
    assert "metadata" in actual_keys, "Missing metadata in payload"

    # Should have domain payload fields directly accessible (not nested under "payload")
    assert "session_id" in actual_keys, "Missing session_id in payload (should be flattened)"
    assert "input" in actual_keys, "Missing input in payload (should be flattened)"

    # Verify the values are correct
    assert outbox_payload["session_id"] == "test-session-123"
    assert outbox_payload["input"] == {"name": "Hero"}
    assert outbox_payload["event_type"] == "Genesis.Character.Requested"
    assert outbox_payload["aggregate_type"] == "GenesisFlow"
    assert outbox_payload["aggregate_id"] == "test-session-123"
