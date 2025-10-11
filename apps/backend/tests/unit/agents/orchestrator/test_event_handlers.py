"""Unit tests for workflow-oriented orchestrator event handlers."""

from __future__ import annotations

from typing import Any

import pytest
from src.agents.orchestrator.event_handlers import CapabilityEventHandlers, WorkflowOrchestrator
from src.agents.orchestrator.types import GenerationData
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

    assert pytest.approx(7.5) == config.QUALITY_THRESHOLD
    assert config.MAX_ATTEMPTS == 3
    assert "Character.Design.Generated" in config.EVENT_TARGET_MAPPING
    assert "Inquiry.Response.Generated" in config.EVENT_TARGET_MAPPING


def test_workflow_orchestrator_routes_generation_events_via_factory():
    action = (
        EventActionBuilder()
        .with_domain_event(
            scope_type="GENESIS",
            session_id="session-1",
            event_action="Character.Proposed",
            payload={"session_id": "session-1"},
        )
        .build()
    )

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

    generation_data = GenerationData(session_id="session-1")
    result = handlers.handle_generation_event(
        msg_type="Character.Design.Generated",
        session_id="session-1",
        data=generation_data,
        correlation_id="corr-1",
        scope_type="GENESIS",
        scope_prefix="genesis",
        causation_id="cause-1",
    )

    assert result is action
    assert factory.calls[0]["msg_type"] == "Character.Design.Generated"
    assert factory.calls[0]["scope_type"] == "GENESIS"


def test_capability_event_handlers_static_methods_use_singleton_orchestrator():
    action = EventAction(task_completion={})
    factory = DummyFactory(return_value=action)
    orchestrator = WorkflowOrchestrator(config=EventHandlerConfig.for_testing(), factory=factory)

    # Inject custom orchestrator as the default singleton
    CapabilityEventHandlers._default_orchestrator = orchestrator

    generation_data = GenerationData(session_id="session-1")
    result = CapabilityEventHandlers.handle_generation_completed(
        msg_type="Character.Design.Generated",
        session_id="session-1",
        data=generation_data,
        correlation_id="corr-1",
        scope_type="GENESIS",
        scope_prefix="GENESIS",
        causation_id="cause-1",
    )

    assert result is action
    assert factory.calls and factory.calls[0]["msg_type"] == "Character.Design.Generated"


def test_inquiry_response_generated_is_recognized_as_generation_event():
    """Test that Inquiry.Response.Generated is recognized as a generation completion event."""
    from src.common.events.mapping import is_generation_completed_event

    assert is_generation_completed_event("Inquiry.Response.Generated")
    assert is_generation_completed_event("Character.Design.Generated")
    assert is_generation_completed_event("Theme.Generated")


def test_inquiry_event_target_mapping():
    """Test that Inquiry.Response.Generated is mapped to inquiry target."""
    from src.agents.orchestrator.workflow_constants import WORKFLOW_DEFAULTS

    assert WORKFLOW_DEFAULTS.EVENT_TARGET_MAPPING.get("Inquiry.Response.Generated") == "inquiry"


def test_inquiry_action_mappings():
    """Test that inquiry has proper action mappings."""
    from src.agents.orchestrator.workflow_constants import WORKFLOW_DEFAULTS

    assert WORKFLOW_DEFAULTS.CONFIRMATION_ACTIONS.get("inquiry") == "Inquiry.Confirmed"
    assert WORKFLOW_DEFAULTS.FAILURE_ACTIONS.get("inquiry") == "Inquiry.Failed"
    assert WORKFLOW_DEFAULTS.REGENERATION_ACTIONS.get("inquiry") == "Inquiry.RegenerationRequested"


def test_workflow_orchestrator_handles_inquiry_response_generated():
    """Test that orchestrator properly handles Inquiry.Response.Generated events."""
    action = (
        EventActionBuilder()
        .with_domain_event(
            scope_type="GENESIS",
            session_id="session-1",
            event_action="Inquiry.Proposed",
            payload={"session_id": "session-1", "content": {"answer": "test answer"}},
        )
        .build()
    )

    factory = DummyFactory(return_value=action)
    config = EventHandlerConfig.for_testing()
    orchestrator = WorkflowOrchestrator(config=config, factory=factory)

    data = GenerationData(session_id="session-1", answer="test answer", query_type="intent_classification")
    result = orchestrator.orchestrate_generation(
        msg_type="Inquiry.Response.Generated",
        session_id="session-1",
        data=data,
        correlation_id="corr-1",
        scope_type="GENESIS",
        scope_prefix="genesis",
        causation_id="cause-1",
    )

    assert result is action
    assert factory.calls and factory.calls[0]["msg_type"] == "Inquiry.Response.Generated"
    assert factory.calls[0]["scope_prefix"] == "genesis"
    assert factory.calls[0]["session_id"] == "session-1"
