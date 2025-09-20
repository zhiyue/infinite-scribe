"""Unit tests for workflow-oriented orchestrator event handlers."""

from __future__ import annotations

from typing import Any

import pytest

from src.agents.orchestrator.event_handlers import CapabilityEventHandlers, WorkflowOrchestrator
from src.agents.orchestrator.types import ConsistencyCheckData, GenerationData, QualityReviewData
from src.agents.orchestrator.workflows import EventAction, EventActionBuilder, EventHandlerConfig


class DummyFactory:
    """Test double that captures orchestrator calls."""

    def __init__(self, return_value: EventAction | None) -> None:
        self.return_value = return_value
        self.calls: list[dict[str, Any]] = []

    def handle_event(
        self,
        *,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        self.calls.append(
            {
                "msg_type": msg_type,
                "session_id": session_id,
                "data": data,
                "correlation_id": correlation_id,
                "scope_type": scope_type,
                "scope_prefix": scope_prefix,
                "causation_id": causation_id,
            }
        )
        return self.return_value


@pytest.fixture(autouse=True)
def reset_capability_event_handlers_singleton():
    """Ensure the class-level orchestrator cache does not leak across tests."""
    original = CapabilityEventHandlers._default_orchestrator
    CapabilityEventHandlers._default_orchestrator = None
    try:
        yield
    finally:
        CapabilityEventHandlers._default_orchestrator = original


def test_event_handler_config_for_genesis_workflow_uses_json_single_source():
    config = EventHandlerConfig.for_genesis_workflow()

    assert config.QUALITY_THRESHOLD == pytest.approx(7.5)
    assert config.MAX_ATTEMPTS == 3
    assert "Character.Design.Generated" in config.EVENT_TARGET_MAPPING


def test_workflow_orchestrator_routes_generation_events_via_factory():
    action = EventActionBuilder().with_domain_event(
        scope_type="GENESIS",
        session_id="session-1",
        event_action="Character.Proposed",
        payload={"session_id": "session-1"},
    ).build()

    factory = DummyFactory(return_value=action)
    config = EventHandlerConfig.for_testing()
    orchestrator = WorkflowOrchestrator(config=config, factory=factory)

    data = GenerationData(session_id="session-1")
    result = orchestrator.orchestrate_generation(
        msg_type="Character.Design.Generated",
        session_id="session-1",
        data=data,
        correlation_id="corr-1",
        scope_type="GENESIS",
        scope_prefix="genesis",
        causation_id="cause-1",
    )

    assert result is action
    assert factory.calls and factory.calls[0]["msg_type"] == "Character.Design.Generated"
    assert factory.calls[0]["scope_prefix"] == "genesis"


def test_capability_event_handlers_instance_delegates_to_orchestrator():
    action = EventAction(domain_event={"scope_type": "GENESIS"})
    factory = DummyFactory(return_value=action)
    config = EventHandlerConfig.for_testing(quality_threshold=6.0)
    orchestrator = WorkflowOrchestrator(config=config, factory=factory)
    handlers = CapabilityEventHandlers(orchestrator=orchestrator)

    review_data = QualityReviewData(session_id="session-1", score=6.0, attempts=1)
    result = handlers.handle_quality_review_event(
        msg_type="Review.Quality.Evaluated",
        session_id="session-1",
        data=review_data,
        correlation_id="corr-1",
        scope_type="GENESIS",
        scope_prefix="genesis",
        causation_id="cause-1",
    )

    assert result is action
    assert factory.calls[0]["msg_type"] == "Review.Quality.Evaluated"
    assert factory.calls[0]["scope_type"] == "GENESIS"


def test_capability_event_handlers_static_methods_use_singleton_orchestrator():
    action = EventAction(task_completion={})
    factory = DummyFactory(return_value=action)
    orchestrator = WorkflowOrchestrator(config=EventHandlerConfig.for_testing(), factory=factory)

    # Inject custom orchestrator as the default singleton
    CapabilityEventHandlers._default_orchestrator = orchestrator

    consistency_data = ConsistencyCheckData(session_id="session-1", ok=True)
    result = CapabilityEventHandlers.handle_consistency_check_result(
        msg_type="Review.Consistency.Checked",
        session_id="session-1",
        data=consistency_data,
        correlation_id="corr-1",
        scope_type="GENESIS",
        causation_id="cause-1",
    )

    assert result is action
    assert factory.calls and factory.calls[0]["msg_type"] == "Review.Consistency.Checked"
