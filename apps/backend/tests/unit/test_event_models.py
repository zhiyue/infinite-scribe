"""
单元测试: 事件相关的 Pydantic 模型
测试 Story 2.1 中定义的事件和命令模型
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.models.db import (
    CommandInboxModel,
    CommandStatus,
    DomainEventModel,
    EventOutboxModel,
    OutboxStatus,
)


class TestDomainEventModel:
    """测试领域事件模型"""

    def test_create_domain_event_minimal(self):
        """测试创建最小化的领域事件"""
        event = DomainEventModel(
            id=1,  # 自增ID
            aggregate_id=str(uuid4()),  # 必须是字符串
            aggregate_type="Novel",
            event_type="NovelCreated",
            payload={"title": "测试小说"},
            correlation_id=None,
            causation_id=None,
            metadata=None,
        )

        assert event.id == 1
        assert event.event_id is not None  # 自动生成的UUID
        assert event.event_version == 1
        assert event.created_at is not None
        assert event.correlation_id is None
        assert event.causation_id is None

    def test_create_domain_event_full(self):
        """测试创建完整的领域事件"""
        event_id = uuid4()
        aggregate_id = str(uuid4())
        correlation_id = uuid4()
        causation_id = uuid4()

        event = DomainEventModel(
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

        event = DomainEventModel(
            id=3,
            aggregate_id=str(uuid4()),
            aggregate_type="Test",
            event_type="TestEvent",
            payload=complex_data,
            correlation_id=None,
            causation_id=None,
            metadata=None,
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
        command = CommandInboxModel(
            id=uuid4(),
            session_id=uuid4(),
            command_type="CreateNovel",
            idempotency_key=str(uuid4()),
            payload={"title": "新小说"},
            error_message=None,
        )

        assert command.id is not None
        assert command.status == CommandStatus.RECEIVED
        assert command.retry_count == 0
        assert command.error_message is None

    def test_create_command_with_retry(self):
        """测试创建带重试信息的命令"""
        command = CommandInboxModel(
            id=uuid4(),
            session_id=uuid4(),
            command_type="GenerateChapter",
            idempotency_key=str(uuid4()),
            payload={"chapter_number": 1},
            status=CommandStatus.FAILED,
            retry_count=2,
            error_message="LLM API timeout",
        )

        assert command.status == CommandStatus.FAILED
        assert command.retry_count == 2
        assert command.error_message == "LLM API timeout"

    def test_command_processed_at(self):
        """测试命令处理时间戳"""
        now = datetime.now(UTC)
        command = CommandInboxModel(
            id=uuid4(),
            session_id=uuid4(),
            command_type="Test",
            idempotency_key=str(uuid4()),
            payload={},
            status=CommandStatus.COMPLETED,
            updated_at=now,  # 使用 updated_at 而不是 processed_at
            error_message=None,
        )

        assert command.updated_at == now


class TestEventOutboxModel:
    """测试事件发件箱模型"""

    def test_create_event_outbox_minimal(self):
        """测试创建最小化的发件箱事件"""
        event = EventOutboxModel(
            id=uuid4(),
            topic="novel.created",
            payload={"novel_id": str(uuid4()), "title": "测试"},
            key=None,
            partition_key=None,
            headers=None,
            last_error=None,
            scheduled_at=None,
            sent_at=None,
        )

        assert event.id is not None
        assert event.status == OutboxStatus.PENDING
        assert event.partition_key is None
        assert event.retry_count == 0

    def test_create_event_outbox_with_partition(self):
        """测试创建带分区键的发件箱事件"""
        aggregate_id = str(uuid4())
        event = EventOutboxModel(
            id=uuid4(),
            topic="chapter.published",
            payload={"chapter_id": str(uuid4()), "novel_id": aggregate_id},
            partition_key=aggregate_id,
            headers={"content-type": "application/json"},
            key=None,
            last_error=None,
            scheduled_at=None,
            sent_at=None,
        )

        assert event.partition_key == aggregate_id
        assert event.headers is not None
        assert event.headers["content-type"] == "application/json"


class TestModelValidation:
    """测试模型验证规则"""

    def test_domain_event_invalid_data(self):
        """测试领域事件无效数据验证"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            # payload 必须是字典
            DomainEventModel(
                id=1,
                aggregate_id=str(uuid4()),
                aggregate_type="Test",
                event_type="TestEvent",
                payload="not a dict",
                correlation_id=None,
                causation_id=None,
                metadata=None,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])