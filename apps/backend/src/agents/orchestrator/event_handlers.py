"""Event Handlers for Capability Events

Contains focused handler functions for different types of capability events,
extracted from the main orchestrator to improve readability and maintainability.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from src.agents.orchestrator.message_factory import MessageFactory


class EventAction(NamedTuple):
    """Represents an action to be taken after handling an event."""

    domain_event: dict[str, Any] | None = None
    task_completion: dict[str, Any] | None = None
    capability_message: dict[str, Any] | None = None


class CapabilityEventHandlers:
    """Handlers for different types of capability events."""

    @staticmethod
    def handle_generation_completed(
        msg_type: str,
        session_id: str,
        data: dict[str, Any],
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle generation completion events (Character.Design.Generated, Theme.Generated).

        Returns:
            EventAction with domain event, task completion, and follow-up message
        """
        if msg_type in {"Character.Design.Generated", "Character.Generated"} and session_id:
            domain_event = {
                "scope_type": scope_type,
                "session_id": session_id,
                "event_action": "Character.Proposed",
                "payload": {"session_id": session_id, "content": data},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
            }

            task_completion = {
                "correlation_id": correlation_id,
                "expect_task_prefix": "Character.Design.Generation",
                "result_data": data,
            }

            capability_message = MessageFactory.create_quality_review_message(
                session_id=session_id, target_type="character", content=data, scope_prefix=scope_prefix
            )

            return EventAction(
                domain_event=domain_event, task_completion=task_completion, capability_message=capability_message
            )

        elif msg_type in {"Outliner.Theme.Generated", "Theme.Generated"} and session_id:
            domain_event = {
                "scope_type": scope_type,
                "session_id": session_id,
                "event_action": "Theme.Proposed",
                "payload": {"session_id": session_id, "content": data},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
            }

            task_completion = {
                "correlation_id": correlation_id,
                "expect_task_prefix": "Outliner.Theme.Generation",
                "result_data": data,
            }

            capability_message = MessageFactory.create_quality_review_message(
                session_id=session_id, target_type="theme", content=data, scope_prefix=scope_prefix
            )

            return EventAction(
                domain_event=domain_event, task_completion=task_completion, capability_message=capability_message
            )

        return None

    @staticmethod
    def handle_quality_review_result(
        msg_type: str,
        session_id: str,
        data: dict[str, Any],
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle quality review result events.

        Returns:
            EventAction with appropriate domain event and possible regeneration message
        """
        if not (msg_type in {"Review.Quality.Evaluated", "Review.Quality.Result"} and session_id):
            return None

        score = float(data.get("score") or data.get("quality_score") or 0.0)
        attempts = int(data.get("attempts") or 0)
        max_attempts = int(data.get("max_attempts") or 3)
        threshold = float(data.get("threshold") or 7.5)
        target_type = str(data.get("target_type") or data.get("entity") or "content").lower()

        task_completion = {
            "correlation_id": correlation_id,
            "expect_task_prefix": "Review.Quality.Evaluation",
            "result_data": data,
        }

        # Quality passed - confirm the content
        if score >= threshold:
            action = MessageFactory.get_confirmation_action(target_type)
            domain_event = {
                "scope_type": scope_type,
                "session_id": session_id,
                "event_action": action,
                "payload": {"session_id": session_id, "score": score},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
            }
            return EventAction(domain_event=domain_event, task_completion=task_completion)

        # Max attempts reached - mark as failed
        if attempts + 1 >= max_attempts:
            action = MessageFactory.get_failure_action(target_type)
            domain_event = {
                "scope_type": scope_type,
                "session_id": session_id,
                "event_action": action,
                "payload": {"session_id": session_id, "score": score, "attempts": attempts + 1},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
            }
            return EventAction(domain_event=domain_event, task_completion=task_completion)

        # Quality not met, but attempts remaining - trigger regeneration
        regen_action = MessageFactory.get_regeneration_action(target_type)
        domain_event = {
            "scope_type": scope_type,
            "session_id": session_id,
            "event_action": regen_action,
            "payload": {"session_id": session_id, "score": score, "attempts": attempts + 1},
            "correlation_id": correlation_id,
            "causation_id": causation_id,
        }

        capability_message = MessageFactory.create_regeneration_message(
            target_type=target_type, session_id=session_id, attempts=attempts, scope_prefix=scope_prefix
        )

        return EventAction(
            domain_event=domain_event, task_completion=task_completion, capability_message=capability_message
        )

    @staticmethod
    def handle_consistency_check_result(
        msg_type: str, session_id: str, data: dict[str, Any], correlation_id: str | None, scope_type: str, causation_id: str | None = None
    ) -> EventAction | None:
        """Handle consistency check result events.

        Returns:
            EventAction with domain event for stage confirmation or failure
        """
        if not (msg_type in {"Review.Consistency.Checked", "Consistency.Checked"} and session_id):
            return None

        # Support three types of judgments: boolean ok/passed; or numeric score >= threshold
        ok = bool(data.get("ok") or data.get("passed"))
        if not ok:
            score = data.get("score") or 0.0
            thr = data.get("threshold") or 1.0
            try:
                ok = float(score) >= float(thr)
            except Exception:
                ok = False

        task_completion = {
            "correlation_id": correlation_id,
            "expect_task_prefix": "Review.Consistency.Check",
            "result_data": data,
        }

        if ok:
            domain_event = {
                "scope_type": scope_type,
                "session_id": session_id,
                "event_action": "Stage.Confirmed",
                "payload": {"session_id": session_id, "result": data},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
            }
        else:
            domain_event = {
                "scope_type": scope_type,
                "session_id": session_id,
                "event_action": "Stage.Failed",
                "payload": {"session_id": session_id, "result": data},
                "correlation_id": correlation_id,
                "causation_id": causation_id,
            }

        return EventAction(domain_event=domain_event, task_completion=task_completion)
