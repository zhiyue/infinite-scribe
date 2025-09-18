"""Unit tests for Genesis Flow switch-stage error handling.

Tests the error handling and response format for the switch-stage endpoint
when validation errors occur.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.routes.v1.genesis.flows import switch_flow_stage
from src.schemas.enums import GenesisStage


@pytest.mark.unit
class TestSwitchStageErrorHandling:
    """Unit tests for switch-stage error handling."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all the dependencies for switch_flow_stage."""
        mock_flow_service = AsyncMock()
        mock_novel_service = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_response = MagicMock()

        return {
            'flow_service': mock_flow_service,
            'novel_service': mock_novel_service,
            'user': mock_user,
            'response': mock_response
        }

    @pytest.mark.asyncio
    async def test_switch_stage_stage_config_incomplete_error(self, mock_dependencies):
        """Test switch_flow_stage returns structured error for stage config incomplete."""
        from src.api.routes.v1.genesis.flows import SwitchStageRequest

        # Arrange
        novel_id = uuid4()
        request = SwitchStageRequest(target_stage=GenesisStage.WORLDVIEW)
        x_correlation_id = "test-correlation-123"

        # Mock the flow service to return a flow
        mock_flow = MagicMock()
        mock_flow.id = uuid4()
        mock_dependencies['flow_service'].get_flow.return_value = mock_flow

        # Mock advance_stage to raise ValueError with specific message (now using Chinese field names)
        error_message = "Required fields are missing - 小说类型, 写作风格. Please complete configuration."
        mock_dependencies['flow_service'].advance_stage.side_effect = ValueError(error_message)

        # Mock novel ownership validation to pass
        mock_dependencies['novel_service'].get_novel.return_value = {"success": True}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await switch_flow_stage(
                novel_id=novel_id,
                request=request,
                response=mock_dependencies['response'],
                current_user=mock_dependencies['user'],
                x_correlation_id=x_correlation_id,
                flow_service=mock_dependencies['flow_service'],
                novel_service=mock_dependencies['novel_service']
            )

        # Assert error structure
        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["type"] == "stage_config_incomplete"
        assert detail["message"] == error_message
        assert detail["user_message"] == "当前阶段配置不完整，请先完成必填字段的配置后再切换到下一阶段"
        assert detail["action_required"] == "complete_current_stage_config"

        # Verify database rollback was called
        mock_dependencies['flow_service'].db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_stage_general_validation_error(self, mock_dependencies):
        """Test switch_flow_stage returns structured error for general validation error."""
        from src.api.routes.v1.genesis.flows import SwitchStageRequest

        # Arrange
        novel_id = uuid4()
        request = SwitchStageRequest(target_stage=GenesisStage.CHARACTERS)
        x_correlation_id = "test-correlation-456"

        # Mock the flow service to return a flow
        mock_flow = MagicMock()
        mock_flow.id = uuid4()
        mock_dependencies['flow_service'].get_flow.return_value = mock_flow

        # Mock advance_stage to raise ValueError with general message
        error_message = "Stage validation failed: invalid transition from INITIAL_PROMPT to CHARACTERS"
        mock_dependencies['flow_service'].advance_stage.side_effect = ValueError(error_message)

        # Mock novel ownership validation to pass
        mock_dependencies['novel_service'].get_novel.return_value = {"success": True}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await switch_flow_stage(
                novel_id=novel_id,
                request=request,
                response=mock_dependencies['response'],
                current_user=mock_dependencies['user'],
                x_correlation_id=x_correlation_id,
                flow_service=mock_dependencies['flow_service'],
                novel_service=mock_dependencies['novel_service']
            )

        # Assert error structure
        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert detail["type"] == "stage_validation_error"
        assert detail["message"] == error_message
        assert detail["user_message"] == "阶段切换失败，请检查当前阶段状态"
        assert detail["action_required"] == "check_stage_status"

        # Verify database rollback was called
        mock_dependencies['flow_service'].db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_stage_successful_flow_continues_normally(self, mock_dependencies):
        """Test switch_flow_stage continues normally when no ValueError occurs."""
        from src.api.routes.v1.genesis.flows import SwitchStageRequest

        # Arrange
        novel_id = uuid4()
        request = SwitchStageRequest(target_stage=GenesisStage.WORLDVIEW)
        x_correlation_id = "test-correlation-789"

        # Create a simple object with the required attributes instead of using MagicMock
        class MockFlow:
            def __init__(self):
                self.id = uuid4()
                self.novel_id = str(novel_id)
                self.status = 'IN_PROGRESS'
                self.current_stage = 'WORLDVIEW'
                self.version = 2
                self.state = {}
                self.created_at = '2024-01-01T00:00:00Z'
                self.updated_at = '2024-01-01T00:00:00Z'

        mock_flow = MockFlow()

        mock_dependencies['flow_service'].get_flow.return_value = mock_flow
        mock_dependencies['flow_service'].advance_stage.return_value = mock_flow
        mock_dependencies['flow_service'].get_current_stage_id.return_value = str(uuid4())
        # get_all_stage_ids should return a dictionary mapping stage to ID
        mock_dependencies['flow_service'].get_all_stage_ids.return_value = {
            GenesisStage.INITIAL_PROMPT: str(uuid4()),
            GenesisStage.WORLDVIEW: str(uuid4())
        }

        # Mock novel ownership validation to pass
        mock_dependencies['novel_service'].get_novel.return_value = {"success": True}

        # Act
        result = await switch_flow_stage(
            novel_id=novel_id,
            request=request,
            response=mock_dependencies['response'],
            current_user=mock_dependencies['user'],
            x_correlation_id=x_correlation_id,
            flow_service=mock_dependencies['flow_service'],
            novel_service=mock_dependencies['novel_service']
        )

        # Assert successful response
        assert result.code == 0
        assert result.msg == "Genesis flow stage switched successfully"
        assert result.data is not None

        # Verify database commit was called
        mock_dependencies['flow_service'].db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_stage_other_exceptions_passthrough(self, mock_dependencies):
        """Test switch_flow_stage allows other exceptions to pass through unchanged."""
        from src.api.routes.v1.genesis.flows import SwitchStageRequest

        # Arrange
        novel_id = uuid4()
        request = SwitchStageRequest(target_stage=GenesisStage.WORLDVIEW)

        # Mock the flow service to return a flow
        mock_flow = MagicMock()
        mock_flow.id = uuid4()
        mock_dependencies['flow_service'].get_flow.return_value = mock_flow

        # Mock advance_stage to raise a different exception (not ValueError)
        mock_dependencies['flow_service'].advance_stage.side_effect = RuntimeError("Database connection failed")

        # Mock novel ownership validation to pass
        mock_dependencies['novel_service'].get_novel.return_value = {"success": True}

        # Act & Assert - Should raise HTTPException with 500 status
        with pytest.raises(HTTPException) as exc_info:
            await switch_flow_stage(
                novel_id=novel_id,
                request=request,
                response=mock_dependencies['response'],
                current_user=mock_dependencies['user'],
                x_correlation_id=None,
                flow_service=mock_dependencies['flow_service'],
                novel_service=mock_dependencies['novel_service']
            )

        # Should be handled by the generic exception handler
        assert exc_info.value.status_code == 500
        assert "Failed to switch Genesis flow stage" in str(exc_info.value.detail)

        # Verify database rollback was called
        mock_dependencies['flow_service'].db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_stage_httpexception_passthrough(self, mock_dependencies):
        """Test switch_flow_stage allows HTTPException to pass through unchanged."""
        from src.api.routes.v1.genesis.flows import SwitchStageRequest

        # Arrange
        novel_id = uuid4()
        request = SwitchStageRequest(target_stage=GenesisStage.WORLDVIEW)

        # Mock novel ownership validation to fail, which will raise HTTPException
        mock_dependencies['novel_service'].get_novel.return_value = {"success": False, "error": "Novel not found"}

        # Act & Assert - HTTPException should pass through unchanged
        with pytest.raises(HTTPException) as exc_info:
            await switch_flow_stage(
                novel_id=novel_id,
                request=request,
                response=mock_dependencies['response'],
                current_user=mock_dependencies['user'],
                x_correlation_id=None,
                flow_service=mock_dependencies['flow_service'],
                novel_service=mock_dependencies['novel_service']
            )

        # Should be the HTTPException from novel validation
        assert exc_info.value.status_code == 404
        assert "Novel not found or you don't have permission to access it" in str(exc_info.value.detail)