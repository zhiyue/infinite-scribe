"""Task Management Module

Handles async task lifecycle management for the orchestrator.
Provides creation and completion operations with idempotency protection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from src.common.utils.datetime_utils import utc_now
from src.db.sql.session import create_sql_session
from src.models.workflow import AsyncTask
from src.schemas.enums import TaskStatus


class TaskIdempotencyChecker:
    """Handles task idempotency validation."""

    @staticmethod
    async def check_existing_task(trig_cmd_id: UUID, task_type: str, db_session) -> AsyncTask | None:
        """Check if a RUNNING/PENDING task already exists to prevent duplicates."""
        existing_stmt = select(AsyncTask).where(
            and_(
                AsyncTask.triggered_by_command_id == trig_cmd_id,
                AsyncTask.task_type == task_type,
                AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
            )
        )
        return await db_session.scalar(existing_stmt)


class TaskCreator:
    """Handles task creation logic."""

    def __init__(self, logger):
        self.log = logger
        self.idempotency_checker = TaskIdempotencyChecker()

    async def create_task(
        self, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """Create an AsyncTask row to track capability execution with idempotency protection."""
        self.log.info(
            "orchestrator_creating_async_task",
            correlation_id=correlation_id,
            session_id=session_id,
            task_type=task_type,
            input_data_keys=list(input_data.keys()) if input_data else [],
        )

        if not task_type:
            self.log.warning(
                "orchestrator_async_task_skipped",
                reason="empty_task_type",
                correlation_id=correlation_id,
                session_id=session_id,
            )
            return

        trig_cmd_id = self._parse_correlation_id(correlation_id)
        if correlation_id and not trig_cmd_id:
            return  # Already logged in _parse_correlation_id

        async with create_sql_session() as db:
            # Check for existing RUNNING/PENDING task to prevent duplicates
            if trig_cmd_id:
                existing_task = await self.idempotency_checker.check_existing_task(trig_cmd_id, task_type, db)
                if existing_task:
                    self.log.info(
                        "async_task_already_exists",
                        correlation_id=correlation_id,
                        task_type=task_type,
                        existing_task_id=str(existing_task.id),
                        existing_status=existing_task.status.value
                        if hasattr(existing_task.status, "value")
                        else str(existing_task.status),
                    )
                    return

            await self._create_new_task(trig_cmd_id, session_id, task_type, input_data, db)

    def _parse_correlation_id(self, correlation_id: str | None) -> UUID | None:
        """Parse correlation_id string to UUID, with error handling."""
        if not correlation_id:
            return None

        try:
            trig_cmd_id = UUID(str(correlation_id))
            self.log.debug(
                "orchestrator_async_task_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
            return trig_cmd_id
        except Exception as e:
            self.log.warning(
                "orchestrator_async_task_correlation_parse_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return None

    async def _create_new_task(
        self, trig_cmd_id: UUID | None, session_id: str, task_type: str, input_data: dict, db_session
    ) -> None:
        """Create new AsyncTask in database."""
        self.log.info(
            "orchestrator_creating_new_async_task",
            task_type=task_type,
            trig_cmd_id=str(trig_cmd_id) if trig_cmd_id else None,
            session_id=session_id,
        )

        task = AsyncTask(
            task_type=task_type,
            triggered_by_command_id=trig_cmd_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
            input_data={"session_id": session_id, **(input_data or {})},
        )
        db_session.add(task)
        await db_session.flush()

        self.log.info(
            "orchestrator_async_task_created_success",
            task_id=str(task.id),
            task_type=task_type,
            status=task.status.value if hasattr(task.status, "value") else str(task.status),
            correlation_id=str(trig_cmd_id) if trig_cmd_id else None,
            session_id=session_id,
        )


class TaskCompleter:
    """Handles task completion logic."""

    def __init__(self, logger):
        self.log = logger

    async def complete_task(
        self, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """Mark latest RUNNING/PENDING AsyncTask (by correlation) as COMPLETED.

        Args:
            correlation_id: UUID string from envelope meta
            expect_task_prefix: Prefix of task_type to match (e.g., "Character.Design.Generation")
            result_data: Result data to store in the task
        """
        self.log.info(
            "orchestrator_completing_async_task",
            correlation_id=correlation_id,
            expect_task_prefix=expect_task_prefix,
            result_data_keys=list(result_data.keys()) if result_data else [],
        )

        if not correlation_id:
            self.log.warning(
                "orchestrator_async_task_complete_skipped",
                reason="no_correlation_id",
                expect_task_prefix=expect_task_prefix,
            )
            return

        trig_cmd_id = self._parse_correlation_id(correlation_id)
        if not trig_cmd_id:
            return  # Already logged in _parse_correlation_id

        async with create_sql_session() as db:
            task = await self._find_task_to_complete(trig_cmd_id, expect_task_prefix, db)
            if task:
                await self._mark_task_completed(task, result_data, db)

    def _parse_correlation_id(self, correlation_id: str) -> UUID | None:
        """Parse correlation_id string to UUID, with error handling."""
        try:
            trig_cmd_id = UUID(str(correlation_id))
            self.log.debug(
                "orchestrator_async_task_complete_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
            return trig_cmd_id
        except Exception as e:
            self.log.warning(
                "orchestrator_async_task_complete_correlation_parse_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return None

    async def _find_task_to_complete(self, trig_cmd_id: UUID, expect_task_prefix: str, db_session) -> AsyncTask | None:
        """Find the most recent RUNNING/PENDING task with matching prefix."""
        self.log.debug(
            "orchestrator_searching_async_task_to_complete",
            trig_cmd_id=str(trig_cmd_id),
            expect_task_prefix=expect_task_prefix,
        )

        # Pick most recent RUNNING/PENDING task with matching prefix
        stmt = (
            select(AsyncTask)
            .where(
                and_(
                    AsyncTask.triggered_by_command_id == trig_cmd_id,
                    AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
                    AsyncTask.task_type.like(f"{expect_task_prefix}%"),
                )
            )
            .order_by(AsyncTask.created_at.desc())
        )
        task = await db_session.scalar(stmt)

        if not task:
            self.log.warning(
                "orchestrator_async_task_not_found_for_completion",
                correlation_id=str(trig_cmd_id),
                expect_task_prefix=expect_task_prefix,
                trig_cmd_id=str(trig_cmd_id),
            )
            return None

        self.log.info(
            "orchestrator_async_task_found_for_completion",
            task_id=str(task.id),
            task_type=task.task_type,
            current_status=task.status.value if hasattr(task.status, "value") else str(task.status),
            created_at=str(task.created_at),
        )

        return task

    async def _mark_task_completed(self, task: AsyncTask, result_data: dict, db_session) -> None:
        """Mark task as completed with result data."""
        task.status = TaskStatus.COMPLETED
        task.completed_at = utc_now()
        task.result_data = result_data or {}
        db_session.add(task)

        self.log.info(
            "orchestrator_async_task_completed_success",
            task_id=str(task.id),
            task_type=task.task_type,
            correlation_id=str(task.triggered_by_command_id),
            result_data_size=len(str(result_data)) if result_data else 0,
        )


class TaskManager:
    """Unified task management interface."""

    def __init__(self, logger):
        self.log = logger
        self.creator = TaskCreator(logger)
        self.completer = TaskCompleter(logger)

    async def create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """Create an async task with idempotency protection."""
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

    async def complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """Complete an async task by correlation_id and task prefix."""
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)
