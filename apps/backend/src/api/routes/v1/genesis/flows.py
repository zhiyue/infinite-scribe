"""Genesis flow management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.repositories.genesis.flow_repository import SqlAlchemyGenesisFlowRepository
from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.flow.genesis_flow_service import GenesisFlowService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import GenesisStage
from src.schemas.genesis import FlowResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class SwitchStageRequest(BaseModel):
    """阶段切换请求"""

    target_stage: GenesisStage


# Service dependency injection
async def get_flow_service(db: AsyncSession = Depends(get_db)) -> GenesisFlowService:
    """Create GenesisFlowService with proper dependency injection."""
    flow_repository = SqlAlchemyGenesisFlowRepository(db)
    return GenesisFlowService(flow_repository, db)


async def get_novel_service() -> NovelService:
    """Create NovelService instance."""
    return NovelService()


async def validate_novel_ownership(
    novel_id: UUID,
    user: User,
    novel_service: NovelService = Depends(get_novel_service),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Validate that the user owns the specified novel."""
    result = await novel_service.get_novel(db, user.id, novel_id)
    if not result["success"]:
        if result["error"] == "Novel not found":
            raise HTTPException(status_code=404, detail="Novel not found or you don't have permission to access it")
        else:
            raise HTTPException(status_code=500, detail="Failed to validate novel ownership")


async def validate_flow_ownership(
    flow_id: UUID,
    user: User,
    flow_service: GenesisFlowService,
    novel_service: NovelService,
) -> None:
    """Validate that the user owns the novel associated with the specified flow."""
    # Get the flow to find its novel_id
    flow = await flow_service.get_flow_by_id(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Genesis flow not found")

    # Validate novel ownership
    await validate_novel_ownership(flow.novel_id, user, novel_service, flow_service.db_session)


@router.post(
    "/flows/{novel_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[FlowResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_or_get_flow(
    novel_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    flow_service: GenesisFlowService = Depends(get_flow_service),
    novel_service: NovelService = Depends(get_novel_service),
) -> ApiResponse[FlowResponse]:
    """Create or ensure a Genesis flow exists for a novel (idempotent)."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Creating/ensuring Genesis flow for novel {novel_id}")

        # Validate novel ownership
        await validate_novel_ownership(novel_id, current_user, novel_service, flow_service.db_session)

        # Use ensure_flow to create or return existing flow
        flow = await flow_service.ensure_flow(novel_id)

        # Commit transaction
        await flow_service.db_session.commit()

        data = FlowResponse.model_validate(flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow created/ensured successfully", data=data)

    except Exception as e:
        await flow_service.db_session.rollback()
        logger.exception(f"Unexpected error in create_or_get_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Genesis flow") from None


@router.get(
    "/flows/{novel_id}",
    response_model=ApiResponse[FlowResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_flow_by_novel(
    novel_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    flow_service: GenesisFlowService = Depends(get_flow_service),
    novel_service: NovelService = Depends(get_novel_service),
) -> ApiResponse[FlowResponse]:
    """Get a Genesis flow by novel ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis flow for novel {novel_id}")

        # Validate novel ownership
        await validate_novel_ownership(novel_id, current_user, novel_service, flow_service.db_session)

        flow = await flow_service.get_flow(novel_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Genesis flow not found for this novel")

        data = FlowResponse.model_validate(flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_flow_by_novel endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Genesis flow") from None


@router.post(
    "/flows/{novel_id}/switch-stage",
    response_model=ApiResponse[FlowResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def switch_flow_stage(
    novel_id: UUID,
    request: SwitchStageRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    flow_service: GenesisFlowService = Depends(get_flow_service),
    novel_service: NovelService = Depends(get_novel_service),
) -> ApiResponse[FlowResponse]:
    """Switch flow to target stage - supports forward/backward/jump navigation."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Switching Genesis flow for novel {novel_id} to stage {request.target_stage}")

        # Validate novel ownership
        await validate_novel_ownership(novel_id, current_user, novel_service, flow_service.db_session)

        # Get current flow
        flow = await flow_service.get_flow(novel_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Genesis flow not found for this novel")

        # Switch to target stage (supports forward/backward/jump navigation)
        updated_flow = await flow_service.advance_stage(
            flow_id=flow.id,
            next_stage=request.target_stage,
        )

        if not updated_flow:
            raise HTTPException(
                status_code=409, detail="Failed to switch stage - invalid stage or flow not found"
            )

        # Commit transaction
        await flow_service.db_session.commit()

        data = FlowResponse.model_validate(updated_flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow stage switched successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        await flow_service.db_session.rollback()
        logger.exception(f"Unexpected error in switch_flow_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to switch Genesis flow stage") from None


@router.post(
    "/flows/{novel_id}/complete",
    response_model=ApiResponse[FlowResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def complete_flow(
    novel_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    flow_service: GenesisFlowService = Depends(get_flow_service),
    novel_service: NovelService = Depends(get_novel_service),
) -> ApiResponse[FlowResponse]:
    """Complete the Genesis flow - direct synchronous operation."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Completing Genesis flow for novel {novel_id}")

        # Validate novel ownership
        await validate_novel_ownership(novel_id, current_user, novel_service, flow_service.db_session)

        # Get current flow
        flow = await flow_service.get_flow(novel_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Genesis flow not found for this novel")

        # Complete the flow
        updated_flow = await flow_service.complete_flow(flow_id=flow.id)

        if not updated_flow:
            raise HTTPException(status_code=409, detail="Failed to complete flow - flow not found or already completed")

        # Commit transaction
        await flow_service.db_session.commit()

        data = FlowResponse.model_validate(updated_flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow completed successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        await flow_service.db_session.rollback()
        logger.exception(f"Unexpected error in complete_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete Genesis flow") from None
