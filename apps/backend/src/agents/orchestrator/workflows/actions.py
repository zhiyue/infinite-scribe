"""Workflow action primitives used by the orchestrator."""

from __future__ import annotations

from typing import Any, NamedTuple


class EventAction(NamedTuple):
    """Represents an action that the orchestrator should take after processing an event."""

    domain_event: dict[str, Any] | None = None
    task_completion: dict[str, Any] | None = None
    capability_message: dict[str, Any] | None = None


class EventActionBuilder:
    """Builder helper for composing :class:`EventAction` objects in a readable way."""

    def __init__(self) -> None:
        self._domain_event: dict[str, Any] | None = None
        self._task_completion: dict[str, Any] | None = None
        self._capability_message: dict[str, Any] | None = None

    def with_domain_event(
        self,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> EventActionBuilder:
        self._domain_event = {
            "scope_type": scope_type,
            "session_id": session_id,
            "event_action": event_action,
            "payload": payload,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
        }
        return self

    def with_task_completion(
        self,
        correlation_id: str | None,
        expect_task_prefix: str,
        result_data: dict[str, Any],
    ) -> EventActionBuilder:
        self._task_completion = {
            "correlation_id": correlation_id,
            "expect_task_prefix": expect_task_prefix,
            "result_data": result_data,
        }
        return self

    def with_capability_message(self, message: dict[str, Any]) -> EventActionBuilder:
        self._capability_message = message
        return self

    def build(self) -> EventAction:
        return EventAction(
            domain_event=self._domain_event,
            task_completion=self._task_completion,
            capability_message=self._capability_message,
        )
