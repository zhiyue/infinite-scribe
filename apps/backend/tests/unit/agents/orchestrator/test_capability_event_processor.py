"""Unit tests for CapabilityEventProcessor and its components.

Tests the capability event processing logic with proper isolation and mocking.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from src.agents.orchestrator.capability_event_processor import (
    CapabilityEventProcessor,
    extract_event_data,
    extract_metadata_field,
    extract_session_and_scope,
)
from src.agents.orchestrator.workflows import EventAction
from src.agents.orchestrator.types import (
    GenerationData,
    MessageContext,
    ScopeInfo,
)
from src.common.events.mapping import normalize_task_type
from src.common.events.config import get_message_type


class TestExtractEventData:
    """Tests for extract_event_data function."""

    def test_extract_with_data_field(self):
        message = {
            "data": {"session_id": "session-123", "result": "success"},
            "other_field": "ignored",
        }

        result = extract_event_data(message)

        assert isinstance(result, GenerationData)
        assert result.model_dump(exclude_none=True) == {
            "session_id": "session-123",
            "result": "success",
        }

    def test_extract_without_data_field(self):
        message = {"session_id": "session-123", "result": "success"}

        result = extract_event_data(message)

        assert isinstance(result, GenerationData)
        assert result.model_dump(exclude_none=True) == message


class TestExtractSessionAndScope:
    """Tests for extract_session_and_scope function."""

    def test_extract_with_session_id(self):
        data = GenerationData(session_id="session-123", other="data")
        context = MessageContext(topic="genesis.character.events")

        session_id, scope_info = extract_session_and_scope(data, context)

        assert session_id == "session-123"
        assert isinstance(scope_info, ScopeInfo)
        assert scope_info.topic == "genesis.character.events"
        assert scope_info.scope_prefix == "Genesis"
        assert scope_info.scope_type == "GENESIS"

    def test_extract_with_aggregate_id(self):
        data = GenerationData(other="data")
        context = MessageContext(topic="character.world.events", meta={"aggregate_id": "session-456"})

        session_id, scope_info = extract_session_and_scope(data, context)

        assert session_id == "session-456"
        assert scope_info.scope_prefix == "Character"
        assert scope_info.scope_type == "CHARACTER"

    def test_extract_no_session(self):
        data = GenerationData()
        context = MessageContext(topic="plot.outline.events")

        session_id, scope_info = extract_session_and_scope(data, context)

        assert session_id == ""
        assert scope_info.scope_prefix == "Plot"
        assert scope_info.scope_type == "PLOT"

    def test_extract_no_topic(self):
        data = GenerationData(session_id="session-123")
        context = MessageContext()

        session_id, scope_info = extract_session_and_scope(data, context)

        assert session_id == "session-123"
        assert scope_info.topic == ""
        assert scope_info.scope_prefix == "Genesis"
        assert scope_info.scope_type == "GENESIS"

    def test_extract_single_word_topic(self):
        data = GenerationData(session_id="session-123")
        context = MessageContext(topic="events")

        session_id, scope_info = extract_session_and_scope(data, context)

        assert session_id == "session-123"
        assert scope_info.scope_prefix == "Genesis"
        assert scope_info.scope_type == "GENESIS"


class TestExtractMetadataField:
    """Tests for extract_metadata_field function."""

    def test_extract_correlation_id(self):
        correlation_id = str(uuid4())
        context = MessageContext(meta={"correlation_id": correlation_id})

        result = extract_metadata_field(context, "correlation_id")

        assert result == correlation_id

    def test_extract_event_id(self):
        event_id = str(uuid4())
        context = MessageContext(meta={"event_id": event_id})

        result = extract_metadata_field(context, "event_id")

        assert result == event_id

    def test_extract_missing_field(self):
        context = MessageContext(meta={})

        result = extract_metadata_field(context, "missing_field")

        assert result is None

    def test_extract_no_meta(self):
        context = MessageContext()

        result = extract_metadata_field(context, "correlation_id")

        assert result is None


class TestCapabilityEventProcessor:
    """Tests for the main capability event processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.processor = CapabilityEventProcessor(self.mock_logger)

    @pytest.mark.asyncio
    async def test_handle_generation_completed_builds_actions(self):
        """Character.Design.Generated 应构建 Proposed + TaskCompletion + QualityReview。"""
        msg_type = "Character.Design.Generated"
        correlation_id = str(uuid4())
        message = {
            "data": {"session_id": "session-123", "character_id": "char-456", "name": "Hero"},
        }
        context = {
            "topic": "genesis.character.events",
            "meta": {"correlation_id": correlation_id, "event_id": str(uuid4())},
        }

        result = await self.processor.handle_capability_event(msg_type, message, context)

        assert result is not None
        assert result.msg_type == msg_type
        assert result.session_id == "session-123"
        assert result.correlation_id == correlation_id

        action = result.action
        assert isinstance(action, EventAction)

        # 领域事件
        assert action.domain_event is not None
        assert action.domain_event["scope_type"] == "GENESIS"
        assert action.domain_event["session_id"] == "session-123"
        assert action.domain_event["event_action"] == "Character.Proposed"
        assert action.domain_event["correlation_id"] == correlation_id

        # 任务完成
        assert action.task_completion is not None
        assert action.task_completion["correlation_id"] == correlation_id
        assert action.task_completion["expect_task_prefix"] == normalize_task_type(msg_type)

        # 质量评审能力消息
        assert action.capability_message is not None
        assert action.capability_message["type"] == get_message_type("quality_review")
        assert action.capability_message["session_id"] == "session-123"
        assert action.capability_message["_topic"].endswith("review.tasks")

    @pytest.mark.asyncio
    async def test_handle_unknown_event_returns_none(self):
        msg_type = "Unknown.Event.Type"
        message = {"data": {"session_id": "session-123", "unknown": "data"}}
        context = {"topic": "genesis.unknown.events"}

        result = await self.processor.handle_capability_event(msg_type, message, context)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_event_data_extraction_and_scope(self):
        msg_type = "Character.Generated"
        message = {
            "data": {"session_id": "session-123", "result": "success"},
        }
        context = {
            "topic": "character.design.events",
            "meta": {"correlation_id": str(uuid4())},
        }

        result = await self.processor.handle_capability_event(msg_type, message, context)
        # 非 generation_completed（严格匹配列表），可能返回 None
        # 这里主要验证不会抛异常，且数据提取正常
        assert isinstance(extract_event_data(message), GenerationData)

    @pytest.mark.asyncio
    async def test_message_without_data_field(self):
        msg_type = "Character.Design.Generated"
        message = {"session_id": "session-123", "result": "success"}
        context = {"topic": "genesis.character.events"}

        result = await self.processor.handle_capability_event(msg_type, message, context)
        assert result is not None
        # 验证使用了整条消息作为数据构建动作
        assert result.action.domain_event is not None

    @pytest.mark.asyncio
    async def test_outliner_theme_generated_target_inference(self):
        """Outliner.Theme.Generated 应推断 target_type 为 theme。"""
        msg_type = "Outliner.Theme.Generated"
        message = {"data": {"session_id": "s-1", "title": "T"}}
        context = {"topic": "genesis.outline.events", "meta": {"correlation_id": str(uuid4())}}

        result = await self.processor.handle_capability_event(msg_type, message, context)
        assert result is not None
        assert result.action.domain_event["event_action"] == "Theme.Proposed"
