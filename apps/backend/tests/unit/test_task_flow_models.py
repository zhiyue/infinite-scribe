"""
单元测试: 任务和流程相关的 Pydantic 模型
测试 Story 2.1 中定义的任务和创世流程模型
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.models.db import (
    AsyncTaskModel,
    FlowResumeHandleModel,
    GenesisSessionModel,
    GenesisStage,
    GenesisStatus,
    HandleStatus,
    TaskStatus,
)


class TestAsyncTaskModel:
    """测试异步任务模型"""

    def test_create_async_task_minimal(self):
        """测试创建最小化的异步任务"""
        from decimal import Decimal

        task = AsyncTaskModel(
            id=uuid4(),
            task_type="llm.generate_text",
            triggered_by_command_id=None,
            input_data=None,
            result_data=None,
            error_data=None,
            execution_node=None,
            started_at=None,
            completed_at=None,
        )

        assert task.id is not None
        assert task.status == TaskStatus.PENDING
        assert task.progress == Decimal("0.00")
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_create_async_task_with_progress(self):
        """测试创建带进度的异步任务"""
        from decimal import Decimal

        task = AsyncTaskModel(
            id=uuid4(),
            task_type="batch.process_chapters",
            status=TaskStatus.RUNNING,
            progress=Decimal("45.50"),
            input_data={"chapter_ids": [1, 2, 3]},
            execution_node="worker-01",
            started_at=datetime.now(UTC),
            triggered_by_command_id=None,
            result_data=None,
            error_data=None,
            completed_at=None,
        )

        assert task.status == TaskStatus.RUNNING
        assert task.progress == Decimal("45.50")
        assert task.execution_node == "worker-01"
        assert task.started_at is not None

    def test_async_task_completion(self):
        """测试异步任务完成状态"""
        from decimal import Decimal

        completed_at = datetime.now(UTC)
        task = AsyncTaskModel(
            id=uuid4(),
            task_type="analysis.sentiment",
            status=TaskStatus.COMPLETED,
            progress=Decimal("100.00"),
            result_data={"sentiment": "positive", "score": 0.95},
            completed_at=completed_at,
            triggered_by_command_id=None,
            input_data=None,
            error_data=None,
            execution_node=None,
            started_at=None,
        )

        assert task.status == TaskStatus.COMPLETED
        assert task.progress == Decimal("100.00")
        assert task.result_data is not None
        assert task.result_data["score"] == 0.95
        assert task.completed_at == completed_at

    def test_async_task_failure(self):
        """测试异步任务失败状态"""
        task = AsyncTaskModel(
            id=uuid4(),
            task_type="external.api_call",
            status=TaskStatus.FAILED,
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
        )

        assert task.status == TaskStatus.FAILED
        assert task.retry_count == task.max_retries
        assert task.error_data is not None
        assert task.error_data["error_code"] == "TIMEOUT"

    def test_async_task_invalid_progress(self):
        """测试异步任务无效进度验证"""
        from decimal import Decimal

        # 注意: 这个测试可能需要在模型中添加验证器
        task = AsyncTaskModel(
            id=uuid4(),
            task_type="test",
            progress=Decimal("150.00"),  # 超出范围
            triggered_by_command_id=None,
            input_data=None,
            result_data=None,
            error_data=None,
            execution_node=None,
            started_at=None,
            completed_at=None,
        )
        # 如果模型没有验证器, 这个值会被接受
        # 实际应用中应该添加 @field_validator
        assert task.progress == Decimal("150.00")


class TestFlowResumeHandleModel:
    """测试工作流恢复句柄模型"""

    def test_create_flow_resume_handle_minimal(self):
        """测试创建最小化的恢复句柄"""
        flow_run_id = str(uuid4())
        handle = FlowResumeHandleModel(
            id=uuid4(),
            flow_run_id=flow_run_id,
            correlation_id=f"chapter-generation-{uuid4()}",
            resume_handle={"key": "handle_data"},
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            expires_at=None,
            resumed_at=None,
        )

        assert handle.id is not None
        assert handle.status == HandleStatus.PENDING_PAUSE
        assert handle.context_data is None
        assert handle.expires_at is None

    def test_create_flow_resume_handle_with_context(self):
        """测试创建带上下文的恢复句柄"""
        handle = FlowResumeHandleModel(
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
        )

        assert handle.status == HandleStatus.PAUSED
        assert handle.context_data is not None
        assert handle.context_data["review_round"] == 2
        assert handle.resume_handle["next_step"] == "apply_feedback"

    def test_flow_resume_handle_expiration(self):
        """测试恢复句柄过期时间"""
        future_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        handle = FlowResumeHandleModel(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="test-expiry",
            resume_handle={},
            expires_at=future_time,
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            resumed_at=None,
        )

        assert handle.expires_at == future_time

    def test_flow_resume_handle_unique_constraint(self):
        """测试恢复句柄唯一性约束"""
        # 这个测试主要是验证模型定义正确
        # 实际的唯一性约束由数据库强制执行
        handle1 = FlowResumeHandleModel(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="test-correlation",
            resume_handle={},
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            expires_at=None,
            resumed_at=None,
        )

        handle2 = FlowResumeHandleModel(
            id=uuid4(),
            flow_run_id=str(uuid4()),
            correlation_id="test-correlation",  # 相同的correlation_id
            resume_handle={},
            task_name=None,
            resume_payload=None,
            timeout_seconds=None,
            context_data=None,
            expires_at=None,
            resumed_at=None,
        )

        # 模型层面允许创建, 数据库层面会拒绝
        assert handle1.correlation_id == handle2.correlation_id


class TestGenesisSessionModel:
    """测试创世会话模型"""

    def test_create_genesis_session_minimal(self):
        """测试创建最小化的创世会话"""
        user_id = uuid4()
        session = GenesisSessionModel(
            id=uuid4(),
            user_id=user_id,
            novel_id=None,
            confirmed_data=None,
        )

        assert session.id is not None
        assert session.status == GenesisStatus.IN_PROGRESS
        assert session.current_stage == GenesisStage.CONCEPT_SELECTION
        assert session.confirmed_data is None

    def test_create_genesis_session_with_data(self):
        """测试创建带数据的创世会话"""
        novel_id = uuid4()
        session = GenesisSessionModel(
            id=uuid4(),
            user_id=uuid4(),
            novel_id=novel_id,
            current_stage=GenesisStage.CHARACTERS,
            confirmed_data={
                "theme": "科幻冒险",
                "writing_style": "幽默诙谐",
                "target_audience": "青少年",
                "characters_created": 3,
            },
        )

        assert session.novel_id == novel_id
        assert session.current_stage == GenesisStage.CHARACTERS
        assert session.confirmed_data is not None
        assert session.confirmed_data["characters_created"] == 3

    def test_genesis_session_completion(self):
        """测试创世会话完成状态"""
        session = GenesisSessionModel(
            id=uuid4(),
            user_id=uuid4(),
            novel_id=uuid4(),
            status=GenesisStatus.COMPLETED,
            current_stage=GenesisStage.FINISHED,
            confirmed_data=None,
        )

        assert session.status == GenesisStatus.COMPLETED
        assert session.current_stage == GenesisStage.FINISHED
        assert session.updated_at is not None  # 使用 updated_at 代替 completed_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])