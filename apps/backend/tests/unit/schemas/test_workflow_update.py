"""Unit tests for workflow update schemas."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from src.common.utils.datetime_utils import utc_now
from src.schemas.enums import CommandStatus, HandleStatus, OutboxStatus, TaskStatus
from src.schemas.workflow.update import (
    AsyncTaskUpdate,
    CommandInboxUpdate,
    EventOutboxUpdate,
    FlowResumeHandleUpdate,
)


class TestCommandInboxUpdate:
    """Test cases for CommandInboxUpdate schema."""

    def test_valid_update_single_field(self):
        """Test valid update with single field."""
        update = CommandInboxUpdate(status=CommandStatus.PROCESSING)

        assert update.status == CommandStatus.PROCESSING
        assert update.error_message is None
        assert update.retry_count is None

    def test_valid_update_multiple_fields(self):
        """Test valid update with multiple fields."""
        update = CommandInboxUpdate(
            status=CommandStatus.COMPLETED,
            error_message="Success",
            retry_count=3
        )

        assert update.status == CommandStatus.COMPLETED
        assert update.error_message == "Success"
        assert update.retry_count == 3

    def test_invalid_update_no_fields(self):
        """Test invalid update with no fields provided."""
        with pytest.raises(ValidationError) as exc_info:
            CommandInboxUpdate()

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_valid_retry_count_zero(self):
        """Test valid retry count of zero."""
        update = CommandInboxUpdate(retry_count=0)
        assert update.retry_count == 0

    def test_invalid_retry_count_negative(self):
        """Test invalid negative retry count."""
        with pytest.raises(ValidationError):
            CommandInboxUpdate(retry_count=-1)


class TestAsyncTaskUpdate:
    """Test cases for AsyncTaskUpdate schema."""

    def test_valid_update_status_only(self):
        """Test valid update with status only."""
        update = AsyncTaskUpdate(status=TaskStatus.RUNNING)

        assert update.status == TaskStatus.RUNNING
        assert update.progress is None

    def test_valid_update_all_fields(self):
        """Test valid update with all fields."""
        now = utc_now()
        result_data = {"key": "value"}
        error_data = {"error": "details"}

        update = AsyncTaskUpdate(
            status=TaskStatus.COMPLETED,
            progress=Decimal("75.50"),
            result_data=result_data,
            error_data=error_data,
            execution_node="node-1",
            retry_count=2,
            started_at=now,
            completed_at=now
        )

        assert update.status == TaskStatus.COMPLETED
        assert update.progress == Decimal("75.50")
        assert update.result_data == result_data
        assert update.error_data == error_data
        assert update.execution_node == "node-1"
        assert update.retry_count == 2
        assert update.started_at == now
        assert update.completed_at == now

    def test_invalid_update_no_fields(self):
        """Test invalid update with no fields provided."""
        with pytest.raises(ValidationError) as exc_info:
            AsyncTaskUpdate()

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_valid_progress_boundary_values(self):
        """Test valid progress boundary values."""
        # Test with 0.00
        update1 = AsyncTaskUpdate(progress=Decimal("0.00"))
        assert update1.progress == Decimal("0.00")

        # Test with 100.00
        update2 = AsyncTaskUpdate(progress=Decimal("100.00"))
        assert update2.progress == Decimal("100.00")


class TestEventOutboxUpdate:
    """Test cases for EventOutboxUpdate schema."""

    def test_valid_update_status_only(self):
        """Test valid update with status only."""
        update = EventOutboxUpdate(status=OutboxStatus.SENT)

        assert update.status == OutboxStatus.SENT
        assert update.retry_count is None

    def test_valid_update_all_fields(self):
        """Test valid update with all fields."""
        sent_time = utc_now()

        update = EventOutboxUpdate(
            status=OutboxStatus.PENDING,
            retry_count=3,
            last_error="Connection timeout",
            sent_at=sent_time
        )

        assert update.status == OutboxStatus.PENDING
        assert update.retry_count == 3
        assert update.last_error == "Connection timeout"
        assert update.sent_at == sent_time

    def test_invalid_update_no_fields(self):
        """Test invalid update with no fields provided."""
        with pytest.raises(ValidationError) as exc_info:
            EventOutboxUpdate()

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_invalid_retry_count_negative(self):
        """Test invalid negative retry count."""
        with pytest.raises(ValidationError):
            EventOutboxUpdate(retry_count=-1)


class TestFlowResumeHandleUpdate:
    """Test cases for FlowResumeHandleUpdate schema."""

    def test_valid_update_status_only(self):
        """Test valid update with status only."""
        update = FlowResumeHandleUpdate(status=HandleStatus.PAUSED)

        assert update.status == HandleStatus.PAUSED
        assert update.resume_payload is None

    def test_valid_update_all_fields(self):
        """Test valid update with all fields."""
        resumed_time = utc_now()
        payload = {"data": {"step": 1, "context": "test"}}

        update = FlowResumeHandleUpdate(
            status=HandleStatus.EXPIRED,
            resume_payload=payload,
            resumed_at=resumed_time
        )

        assert update.status == HandleStatus.EXPIRED
        assert update.resume_payload == payload
        assert update.resumed_at == resumed_time

    def test_invalid_update_no_fields(self):
        """Test invalid update with no fields provided."""
        with pytest.raises(ValidationError) as exc_info:
            FlowResumeHandleUpdate()

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_valid_empty_resume_payload(self):
        """Test valid empty resume payload."""
        update = FlowResumeHandleUpdate(resume_payload={})
        assert update.resume_payload == {}

    def test_valid_complex_resume_payload(self):
        """Test valid complex resume payload."""
        complex_payload = {
            "step_id": "step-1",
            "context": {
                "variables": {"x": 1, "y": "test"},
                "state": "paused"
            },
            "metadata": ["tag1", "tag2"]
        }

        update = FlowResumeHandleUpdate(resume_payload=complex_payload)
        assert update.resume_payload == complex_payload
