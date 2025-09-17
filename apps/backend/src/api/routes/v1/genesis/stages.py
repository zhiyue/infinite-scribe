"""Genesis stage record management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.flow.genesis_flow_service import GenesisFlowService
from src.common.services.genesis.stage.genesis_stage_service import GenesisStageService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import GenesisStage
from src.schemas.genesis import CreateStageRequest, StageResponse

from .dependencies import get_flow_service, get_genesis_stage_service, get_novel_service
from .validation import validate_novel_ownership

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/flows/{novel_id}/stages/{stage}",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[StageResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_stage(
    novel_id: UUID,
    stage: GenesisStage,
    request: CreateStageRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
    novel_service: NovelService = Depends(get_novel_service),
    flow_service: GenesisFlowService = Depends(get_flow_service),
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[StageResponse]:
    """Create a new Genesis stage record for a specific flow and stage type."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Creating Genesis stage {stage} for novel {novel_id}")

        # Validate novel ownership
        await validate_novel_ownership(novel_id, current_user, novel_service, db)

        # Get or ensure flow exists
        flow = await flow_service.ensure_flow(novel_id)
        if not flow:
            raise HTTPException(status_code=500, detail="Failed to ensure Genesis flow exists")

        # Create stage record
        stage_record = await stage_service.create_stage(
            flow_id=flow.id,
            stage=stage,
            config=request.config,
        )

        data = StageResponse.from_orm(stage_record)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stage created successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in create_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Genesis stage")














