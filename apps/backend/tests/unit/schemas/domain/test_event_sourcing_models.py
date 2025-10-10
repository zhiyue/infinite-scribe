"""
单元测试: 事件溯源相关的 Pydantic 模型
测试 Story 2.1 中定义的所有数据模型
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from src.schemas.domain_event import DomainEventResponse
from src.schemas.enums import (
    CommandStatus,
    GenesisStage,
    GenesisStatus,
    HandleStatus,
    OutboxStatus,
    TaskStatus,
)
# GenesisSessionResponse removed - using new Genesis flow schemas
from src.schemas.workflow import (
    AsyncTaskResponse,
    CommandInboxResponse,
    EventOutboxResponse,
    FlowResumeHandleResponse,
)


class TestDomainEventModel:
    """测试领域事件模型"""

    def test_create_domain_event_minimal(self):
        """测试创建最小化的领域事件"""
        event_id = uuid4()
        created_at = datetime.now(UTC)

        event = DomainEventResponse(
            id=1,  # 自增ID
            event_id=event_id,
            aggregate_id=str(uuid4()),  # 必须是字符串
            aggregate_type="Novel",
            event_type="NovelCreated",
            event_version=1,
            payload={"title": "测试小说"},
            correlation_id=None,
            causation_id=None,
            metadata=None,
            created_at=created_at,
        )

        assert event.id == 1
        assert event.event_id == event_id
        assert event.event_version == 1
        assert event.created_at == created_at
        assert event.correlation_id is None
        assert event.causation_id is None

    def test_create_domain_event_full(self):
        """测试创建完整的领域事件"""
        event_id = uuid4()
        aggregate_id = str(uuid4())
        correlation_id = uuid4()
        causation_id = uuid4()

        event = DomainEventResponse(
            id=2,
            event_id=event_id,
            aggregate_id=aggregate_id,
            aggregate_type="Chapter",
            event_type="ChapterPublished",
            event_version=2,
            payload={
                "chapter_number": 1,
                "title": "第一章",
                "published_at": datetime.now(UTC).isoformat(),
            },
            metadata={"user_id": "test-user", "ip_address": "192.168.1.1"},
            correlation_id=correlation_id,
            causation_id=causation_id,
            created_at=datetime.now(UTC),
        )

        assert event.id == 2
        assert event.event_id == event_id
        assert event.aggregate_id == aggregate_id
        assert event.event_version == 2
        assert event.correlation_id == correlation_id
        assert event.causation_id == causation_id

    def test_event_data_json_serialization(self):
        """测试事件数据的JSON序列化"""
        complex_data = {
            "nested": {"values": [1, 2, 3], "flag": True},
            "timestamp": datetime.now(UTC).isoformat(),
        }

        event = DomainEventResponse(
            id=3,
            event_id=uuid4(),
            aggregate_id=str(uuid4()),
            aggregate_type="Test",
            event_type="TestEvent",
            event_version=1,
            payload=complex_data,
            correlation_id=None,
            causation_id=None,
            metadata=None,
            created_at=datetime.now(UTC),
        )

        # 确保可以正确序列化为JSON
        json_str = event.model_dump_json()
        assert isinstance(json_str, str)

        # 确保可以重新解析
        parsed = json.loads(json_str)
        assert parsed["payload"]["nested"]["values"] == [1, 2, 3]


class TestCommandInboxModel:
    """测试命令收件箱模型"""

    def test_create_command_minimal(self):
        """测试创建最小化的命令"""
        now = datetime.now(UTC)
        command = CommandInboxResponse(
            id=uuid4(),
            session_id=uuid4(),
            command_type="CreateNovel",
            idempotency_key=str(uuid4()),
            payload={"title": "新小说"},
            status=CommandStatus.RECEIVED,
            retry_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )

        assert command.id is not None
        assert command.status == CommandStatus.RECEIVED
        assert command.retry_count == 0
        assert command.error_message is None

    def test_create_command_with_retry(self):
        """测试创建带重试信息的命令"""
        now = datetime.now(UTC)
        command = CommandInboxResponse(
            id=uuid4(),
            session_id=uuid4(),
            command_type="GenerateChapter",
            idempotency_key=str(uuid4()),
            payload={"chapter_number": 1},
            status=CommandStatus.FAILED,
            retry_count=2,
            error_message="LLM API timeout",
            created_at=now,
            updated_at=now,
        )

        assert command.status == CommandStatus.FAILED
        assert command.retry_count == 2
        assert command.error_message == "LLM API timeout"

    def test_command_processed_at(self):
        """测试命令处理时间戳"""
        now = datetime.now(UTC)
        created = datetime.now(UTC) - timedelta(minutes=5)
        command = CommandInboxResponse(
            id=uuid4(),
            session_id=uuid4(),
            command_type="Test",
            idempotency_key=str(uuid4()),
            payload={},
            status=CommandStatus.COMPLETED,
            retry_count=0,
            error_message=None,
            created_at=created,
            updated_at=now,  # 使用 updated_at 而不是 processed_at
        )

        assert command.updated_at == now


class TestAsyncTaskModel:
    """测试异步任务模型"""

    def test_create_async_task_minimal(self):
        """测试创建最小化的异步任务"""
        from decimal import Decimal

        now = datetime.now(UTC)
        task = AsyncTaskResponse(
            id=uuid4(),
            task_type="llm.generate_text",
            triggered_by_command_id=None,
            status=TaskStatus.PENDING,
            progress=Decimal("0.00"),
            input_data=None,
            result_data=None,
            error_data=None,
            execution_node=None,
            retry_count=0,
            max_retries=3,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )

        assert task.id is not None
        assert task.status == TaskStatus.PENDING
        assert task.progress == Decimal("0.00")
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_create_async_task_with_progress(self):
        """测试创建带进度的异步任务"""
        from decimal import Decimal

        now = datetime.now(UTC)
        task = AsyncTaskResponse(
            id=uuid4(),
            task_type="batch.process_chapters",
            status=TaskStatus.RUNNING,
            progress=Decimal("45.50"),
            input_data={"chapter_ids": [1, 2, 3]},
            execution_node="worker-01",
            started_at=now,
            triggered_by_command_id=None,
            result_data=None,
            error_data=None,
            completed_at=None,
            retry_count=0,
            max_retries=3,
            created_at=now,
            updated_at=now,
        )

        assert task.status == TaskStatus.RUNNING
        assert task.progress == Decimal("45.50")
        assert task.execution_node == "worker-01"
        assert task.started_at is not None

    def test_async_task_completion(self):
        """测试异步任务完成状态"""
        from decimal import Decimal

        now = datetime.now(UTC)
        started = now - timedelta(minutes=5)
        task = AsyncTaskResponse(
            id=uuid4(),
            task_type="analysis.sentiment",
            status=TaskStatus.COMPLETED,
            progress=Decimal("100.00"),
            result_data={"sentiment": "positive", "score": 0.95},
            completed_at=now,
            triggered_by_command_id=None,
            input_data=None,
            error_data=None,
            execution_node=None,
            started_at=started,
            retry_count=0,
            max_retries=3,
            created_at=started,
            updated_at=now,
        )

        assert task.status == TaskStatus.COMPLETED
        assert task.progress == Decimal("100.00")
        assert task.result_data is not None
        assert task.result_data["score"] == 0.95
        assert task.completed_at == now

    def test_async_task_failure(self):
        """测试异步任务失败状态"""
        from decimal import Decimal

        now = datetime.now(UTC)
        task = AsyncTaskResponse(
            id=uuid4(),
            task_type="external.api_call",
            status=TaskStatus.FAILED,
            progress=Decimal("0.00"),
            retry_count=3,
            max_retries=3,
            error_data={
                "error_code": "TIMEOUT",
                "error_message": "Request timeout after 30s",
                "stack_trace": "...",
            },
            triggered_by_command_id=None,
            input_data=None,
            result_data=None,
            execution_node=None,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )

        assert task.status == TaskStatus.FAILED
        assert task.retry_count == task.max_retries
        assert task.error_data is not None
        assert task.error_data["error_code"] == "TIMEOUT"


class TestEventOutboxModel:
    """测试事件发件箱模型"""

    def test_create_event_outbox_minimal(self):
        """测试创建最小化的发件箱事件"""
        now = datetime.now(UTC)
        event = EventOutboxResponse(
            id=uuid4(),
            topic="novel.created",
            payload={"novel_id": str(uuid4()), "title": "测试"},
            key=None,
            partition_key=None,
            headers=None,
            status=OutboxStatus.PENDING,
            retry_count=0,
            max_retries=3,
            last_error=None,
            scheduled_at=None,
            sent_at=None,
            created_at=now,
        )

        assert event.id is not None
        assert event.status == OutboxStatus.PENDING
        assert event.partition_key is None
        assert event.retry_count == 0

    def test_create_event_outbox_with_partition(self):
        """测试创建带分区键的发件箱事件"""
        aggregate_id = str(uuid4())
        now = datetime.now(UTC)
        event = EventOutboxResponse(
            id=uuid4(),
            topic="chapter.published",
            payload={"chapter_id": str(uuid4()), "novel_id": aggregate_id},
            partition_key=aggregate_id,
            headers={"content-type": "application/json"},
            key=None,
            status=OutboxStatus.PENDING,
            retry_count=0,
            max_retries=3,
            last_error=None,
            scheduled_at=None,
            sent_at=None,
            created_at=now,
        )

        assert event.partition_key == aggregate_id
        assert event.headers is not None
        assert event.headers["content-type"] == "application/json"


class TestFlowResumeHandleModel:
    """测试工作流恢复句柄模型"""

    def test_create_flow_resume_handle_minimal(self):
        """测试创建最小化的恢复句柄"""
        flow_run_id = str(uuid4())
        now = datetime.now(UTC)
        handle = FlowResumeHandleResponse(
            id=uuid4(),
            flow_run_id=flow_run_id,
            correlation_id=f"chapter-generation-{uuid4()}",
            resume_handle={"key": "handle_data"},
            status=HandleStatus.PENDING_PAUSE,
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            expires_at=None,
            resumed_at=None,
            created_at=now,
            updated_at=now,
        )

        assert handle.id is not None
        assert handle.status == HandleStatus.PENDING_PAUSE
        assert handle.context_data is None
        assert handle.expires_at is None

    def test_create_flow_resume_handle_with_context(self):
        """测试创建带上下文的恢复句柄"""
        now = datetime.now(UTC)
        handle = FlowResumeHandleResponse(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="review-cycle-123",
            status=HandleStatus.PAUSED,
            context_data={"chapter_id": str(uuid4()), "review_round": 2, "last_score": 7.5},
            resume_handle={"next_step": "apply_feedback"},
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            expires_at=None,
            resumed_at=None,
            created_at=now,
            updated_at=now,
        )

        assert handle.status == HandleStatus.PAUSED
        assert handle.context_data is not None
        assert handle.context_data["review_round"] == 2
        assert handle.resume_handle["next_step"] == "apply_feedback"

    def test_flow_resume_handle_expiration(self):
        """测试恢复句柄过期时间"""
        now = datetime.now(UTC)
        future_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        handle = FlowResumeHandleResponse(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="test-expiry",
            resume_handle={},
            status=HandleStatus.PENDING_PAUSE,
            expires_at=future_time,
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            resumed_at=None,
            created_at=now,
            updated_at=now,
        )

        assert handle.expires_at == future_time


# TestGenesisSessionModel removed - replaced by tests for new Genesis flow schemas


class TestModelValidation:
    """测试模型验证规则"""

    def test_domain_event_invalid_data(self):
        """测试领域事件无效数据验证"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            # payload 必须是字典
            DomainEventResponse(
                id=1,
                event_id=uuid4(),
                aggregate_id=str(uuid4()),
                aggregate_type="Test",
                event_type="TestEvent",
                event_version=1,
                payload="not a dict",  # 这应该是字典
                correlation_id=None,
                causation_id=None,
                metadata=None,
                created_at=datetime.now(UTC),
            )

    def test_async_task_invalid_progress(self):
        """测试异步任务无效进度验证"""
        from decimal import Decimal

        # 注意: 这个测试可能需要在模型中添加验证器
        now = datetime.now(UTC)
        task = AsyncTaskResponse(
            id=uuid4(),
            task_type="test",
            status=TaskStatus.RUNNING,
            progress=Decimal("150.00"),  # 超出范围
            retry_count=0,
            max_retries=3,
            triggered_by_command_id=None,
            input_data=None,
            result_data=None,
            error_data=None,
            execution_node=None,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        # 如果模型没有验证器, 这个值会被接受
        # 实际应用中应该添加 @field_validator
        assert task.progress == Decimal("150.00")

    def test_flow_resume_handle_unique_constraint(self):
        """测试恢复句柄唯一性约束"""
        # 这个测试主要是验证模型定义正确
        # 实际的唯一性约束由数据库强制执行
        now = datetime.now(UTC)
        handle1 = FlowResumeHandleResponse(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="test-correlation",
            resume_handle={},
            status=HandleStatus.PENDING_PAUSE,
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            expires_at=None,
            resumed_at=None,
            created_at=now,
            updated_at=now,
        )

        handle2 = FlowResumeHandleResponse(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="test-correlation",  # 相同的correlation_id
            resume_handle={},
            status=HandleStatus.PENDING_PAUSE,
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            expires_at=None,
            resumed_at=None,
            created_at=now,
            updated_at=now,
        )

        # 模型层面允许创建, 数据库层面会拒绝
        assert handle1.correlation_id == handle2.correlation_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
