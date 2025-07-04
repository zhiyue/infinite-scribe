"""Unit tests for command processors."""

import json
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.common.services.command_service import CommandService
from src.models.api import (
    CommandRequest,
    RequestConceptGenerationCommand,
    ConfirmStageCommand,
    SubmitFeedbackCommand
)


@pytest.fixture
def command_service():
    """Create command service instance."""
    from src.common.services.event_publisher import EventPublisher
    event_publisher = EventPublisher()
    return CommandService(event_publisher)


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


class TestRequestConceptGenerationProcessor:
    """Test RequestConceptGeneration command processor."""
    
    @pytest.mark.asyncio
    async def test_process_request_concept_generation(self, command_service, mock_session):
        """Test processing RequestConceptGeneration command."""
        # Setup
        session_id = str(uuid4())
        correlation_id = str(uuid4())
        command = CommandRequest(
            session_id=session_id,
            command_type="RequestConceptGeneration",
            payload={
                "topic": "科幻小说创作",
                "requirements": ["创新性", "逻辑性", "可读性"]
            }
        )
        
        # Execute
        events = await command_service._process_request_concept_generation(
            command, correlation_id, mock_session
        )
        
        # Assertions
        assert len(events) == 1
        event = events[0]
        assert event['event_type'] == 'Genesis.Session.ConceptGenerationRequested'
        assert event['aggregate_id'] == session_id
        assert event['causation_id'] == correlation_id
        
        # Check event data
        event_data = event['event_data']
        assert event_data['session_id'] == session_id
        assert event_data['topic'] == "科幻小说创作"
        assert event_data['requirements'] == ["创新性", "逻辑性", "可读性"]
        assert 'timestamp' in event_data
    
    @pytest.mark.asyncio
    async def test_process_request_concept_generation_invalid_payload(self, command_service, mock_session):
        """Test processing RequestConceptGeneration with invalid payload."""
        # Setup
        command = CommandRequest(
            session_id=str(uuid4()),
            command_type="RequestConceptGeneration",
            payload={
                "invalid_field": "value"
            }
        )
        
        # Execute and expect error
        with pytest.raises(Exception):
            await command_service._process_request_concept_generation(
                command, str(uuid4()), mock_session
            )


class TestConfirmStageProcessor:
    """Test ConfirmStage command processor."""
    
    @pytest.mark.asyncio
    async def test_process_confirm_stage(self, command_service, mock_session):
        """Test processing ConfirmStage command."""
        # Setup
        session_id = str(uuid4())
        correlation_id = str(uuid4())
        command = CommandRequest(
            session_id=session_id,
            command_type="ConfirmStage",
            payload={
                "stage_name": "CONCEPT_SELECTION",
                "confirmation_data": {
                    "selected_concept": "时空旅行者",
                    "reasons": ["创新", "有趣"]
                }
            }
        )
        
        # Execute
        events = await command_service._process_confirm_stage(
            command, correlation_id, mock_session
        )
        
        # Assertions
        assert len(events) == 1
        event = events[0]
        assert event['event_type'] == 'Genesis.Session.StageConfirmed'
        assert event['aggregate_id'] == session_id
        assert event['causation_id'] == correlation_id
        
        # Check event data
        event_data = event['event_data']
        assert event_data['session_id'] == session_id
        assert event_data['stage_name'] == "CONCEPT_SELECTION"
        assert event_data['confirmation_data']['selected_concept'] == "时空旅行者"
        assert 'timestamp' in event_data
    
    @pytest.mark.asyncio
    async def test_process_confirm_stage_invalid_payload(self, command_service, mock_session):
        """Test processing ConfirmStage with invalid payload."""
        # Setup
        command = CommandRequest(
            session_id=str(uuid4()),
            command_type="ConfirmStage",
            payload={
                "invalid_field": "value"
            }
        )
        
        # Execute and expect error
        with pytest.raises(Exception):
            await command_service._process_confirm_stage(
                command, str(uuid4()), mock_session
            )


class TestSubmitFeedbackProcessor:
    """Test SubmitFeedback command processor."""
    
    @pytest.mark.asyncio
    async def test_process_submit_feedback(self, command_service, mock_session):
        """Test processing SubmitFeedback command."""
        # Setup
        session_id = str(uuid4())
        correlation_id = str(uuid4())
        command = CommandRequest(
            session_id=session_id,
            command_type="SubmitFeedback",
            payload={
                "feedback_type": "QUALITY_RATING",
                "feedback_data": {
                    "content_quality": "excellent",
                    "comments": "非常满意生成的内容"
                },
                "rating": 5
            }
        )
        
        # Execute
        events = await command_service._process_submit_feedback(
            command, correlation_id, mock_session
        )
        
        # Assertions
        assert len(events) == 1
        event = events[0]
        assert event['event_type'] == 'Genesis.Session.FeedbackSubmitted'
        assert event['aggregate_id'] == session_id
        assert event['causation_id'] == correlation_id
        
        # Check event data
        event_data = event['event_data']
        assert event_data['session_id'] == session_id
        assert event_data['feedback_type'] == "QUALITY_RATING"
        assert event_data['rating'] == 5
        assert event_data['feedback_data']['content_quality'] == "excellent"
        assert 'timestamp' in event_data
    
    @pytest.mark.asyncio
    async def test_process_submit_feedback_invalid_payload(self, command_service, mock_session):
        """Test processing SubmitFeedback with invalid payload."""
        # Setup
        command = CommandRequest(
            session_id=str(uuid4()),
            command_type="SubmitFeedback",
            payload={
                "invalid_field": "value"
            }
        )
        
        # Execute and expect error
        with pytest.raises(Exception):
            await command_service._process_submit_feedback(
                command, str(uuid4()), mock_session
            )


class TestCommandProcessorValidation:
    """Test command processor validation logic."""
    
    def test_command_processors_mapping(self, command_service):
        """Test that all expected command processors are mapped."""
        expected_processors = {
            'RequestConceptGeneration',
            'ConfirmStage',
            'SubmitFeedback'
        }
        
        actual_processors = set(command_service.command_processors.keys())
        
        assert expected_processors == actual_processors
    
    def test_command_processors_are_callable(self, command_service):
        """Test that all command processors are callable."""
        for processor_name, processor_func in command_service.command_processors.items():
            assert callable(processor_func), f"Processor {processor_name} is not callable"
    
    @pytest.mark.asyncio
    async def test_processor_error_handling(self, command_service, mock_session):
        """Test error handling in command processors."""
        # Setup command with invalid session to trigger error
        command = CommandRequest(
            session_id="invalid-session",
            command_type="RequestConceptGeneration",
            payload={
                "topic": None,  # Invalid topic
                "requirements": []
            }
        )
        
        # Execute and expect error to be raised
        with pytest.raises(Exception):
            await command_service._process_request_concept_generation(
                command, str(uuid4()), mock_session
            )