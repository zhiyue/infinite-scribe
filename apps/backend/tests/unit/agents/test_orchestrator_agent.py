import asyncio

from src.agents.orchestrator.agent import OrchestratorAgent


class Calls:
    def __init__(self):
        self.persist = []
        self.created = []
        self.completed = []


def test_command_to_character_requested_and_task(monkeypatch):
    agent = OrchestratorAgent()
    calls = Calls()

    async def fake_persist(scope_type, session_id, event_action, payload, correlation_id):
        calls.persist.append((scope_type, session_id, event_action, payload, correlation_id))

    async def fake_create(correlation_id, session_id, task_type, input_data):
        calls.created.append((correlation_id, session_id, task_type, input_data))

    monkeypatch.setattr(agent, "_persist_domain_event", fake_persist)
    monkeypatch.setattr(agent, "_create_async_task", fake_create)

    evt = {
        "event_type": "Genesis.Session.Command.Received",
        "aggregate_id": "session-1",
        "payload": {"command_type": "Character.Request", "payload": {"name": "Hero"}},
        "metadata": {"correlation_id": "c-1"},
    }
    out = asyncio.run(agent.process_message(evt))

    # Domain projection to Requested
    assert any(a[2] == "Character.Requested" for a in calls.persist)
    # Capability task emitted to genesis.character.tasks
    assert out is not None and out.get("_topic") == "genesis.character.tasks"
    # Async task created
    assert calls.created and calls.created[0][2].startswith("Character.Design.Generation")


def test_capability_generated_triggers_review(monkeypatch):
    agent = OrchestratorAgent()
    calls = Calls()

    async def fake_persist(scope_type, session_id, event_action, payload, correlation_id):
        calls.persist.append((scope_type, session_id, event_action))

    async def fake_complete(correlation_id, expect_task_prefix, result_data):
        calls.completed.append((correlation_id, expect_task_prefix))

    monkeypatch.setattr(agent, "_persist_domain_event", fake_persist)
    monkeypatch.setattr(agent, "_complete_async_task", fake_complete)

    msg = {"type": "Character.Design.Generated", "data": {"session_id": "s1", "correlation_id": "c-2"}}
    ctx = {"topic": "genesis.character.events"}
    out = asyncio.run(agent.process_message(msg, ctx))

    # Proposed fact written
    assert any(a[2] == "Character.Proposed" for a in calls.persist)
    # Review task emitted
    assert out and out.get("_topic") == "genesis.review.tasks" and out.get("type").endswith("EvaluationRequested")
    # Async task completed for generation
    assert calls.completed and calls.completed[0][1].startswith("Character.Design.Generation")


def test_quality_review_decision_paths(monkeypatch):
    agent = OrchestratorAgent()
    calls = Calls()

    async def fake_persist(scope_type, session_id, event_action, payload, correlation_id):
        calls.persist.append((event_action, payload))

    async def fake_complete(correlation_id, expect_task_prefix, result_data):
        calls.completed.append(expect_task_prefix)

    monkeypatch.setattr(agent, "_persist_domain_event", fake_persist)
    monkeypatch.setattr(agent, "_complete_async_task", fake_complete)

    # Pass
    msg_pass = {
        "type": "Review.Quality.Evaluated",
        "data": {"session_id": "s1", "score": 8.0, "target_type": "character"},
    }
    assert asyncio.run(agent.process_message(msg_pass, {"topic": "genesis.review.events"})) is None
    assert any(a[0] == "Character.Confirmed" for a in calls.persist)

    calls.persist.clear()
    # Retry
    msg_retry = {
        "type": "Review.Quality.Evaluated",
        "data": {"session_id": "s1", "score": 6.0, "attempts": 0, "max_attempts": 3, "target_type": "theme"},
    }
    out = asyncio.run(agent.process_message(msg_retry, {"topic": "genesis.review.events"}))
    assert any(a[0] == "Theme.RegenerationRequested" for a in calls.persist)
    assert out and out.get("_topic") == "genesis.outline.tasks"

    calls.persist.clear()
    # Fail after max attempts
    msg_fail = {
        "type": "Review.Quality.Evaluated",
        "data": {"session_id": "s1", "score": 5.0, "attempts": 2, "max_attempts": 3, "target_type": "character"},
    }
    assert asyncio.run(agent.process_message(msg_fail, {"topic": "genesis.review.events"})) is None
    assert any(a[0] == "Character.Failed" for a in calls.persist)


def test_consistency_checked_confirms_or_fails(monkeypatch):
    agent = OrchestratorAgent()
    calls = Calls()

    async def fake_persist(scope_type, session_id, event_action, payload, correlation_id):
        calls.persist.append((event_action, payload))

    async def fake_complete(correlation_id, expect_task_prefix, result_data):
        calls.completed.append(expect_task_prefix)

    monkeypatch.setattr(agent, "_persist_domain_event", fake_persist)
    monkeypatch.setattr(agent, "_complete_async_task", fake_complete)

    ok_msg = {"type": "Review.Consistency.Checked", "data": {"session_id": "s1", "ok": True}}
    assert asyncio.run(agent.process_message(ok_msg, {"topic": "genesis.review.events"})) is None
    assert any(a[0] == "Stage.Confirmed" for a in calls.persist)

    calls.persist.clear()
    fail_msg = {"type": "Review.Consistency.Checked", "data": {"session_id": "s1", "ok": False}}
    assert asyncio.run(agent.process_message(fail_msg, {"topic": "genesis.review.events"})) is None
    assert any(a[0] == "Stage.Failed" for a in calls.persist)
