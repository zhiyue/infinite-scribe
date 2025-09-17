"""Genesis stage record management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.genesis import GenesisStageService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import GenesisStage, StageStatus
from src.schemas.genesis import CreateStageRequest, StageResponse, UpdateStageRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Service instance
stage_service = GenesisStageService()


@router.post(
    "/stages",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[StageResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_stage(
    request: CreateStageRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageResponse]:
    """Create a new Genesis stage record."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Creating Genesis stage {request.stage} for flow {request.flow_id}")

        stage_record = await stage_service.create_stage(
            db=db,
            flow_id=request.flow_id,
            stage=request.stage,
            config=request.config,
            iteration_count=request.iteration_count,
        )

        data = StageResponse.from_orm(stage_record)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stage created successfully", data=data)

    except Exception as e:
        logger.exception(f"Unexpected error in create_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Genesis stage")


@router.get(
    "/stages/{stage_id}",
    response_model=ApiResponse[StageResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_stage(
    stage_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageResponse]:
    """Get a Genesis stage record by ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis stage {stage_id}")

        stage_record = await stage_service.get_stage(db, stage_id)
        if not stage_record:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        data = StageResponse.from_orm(stage_record)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stage retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Genesis stage")


@router.get(
    "/stages/by-flow-and-stage/{flow_id}/{stage}",
    response_model=ApiResponse[StageResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_stage_by_flow_and_stage(
    flow_id: UUID,
    stage: GenesisStage,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageResponse]:
    """Get the latest stage record for a specific flow and stage type."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis stage {stage} for flow {flow_id}")

        stage_record = await stage_service.get_stage_by_flow_and_stage(db, flow_id, stage)
        if not stage_record:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        data = StageResponse.from_orm(stage_record)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stage retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage_by_flow_and_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Genesis stage")


@router.patch(
    "/stages/{stage_id}",
    response_model=ApiResponse[StageResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def update_stage(
    stage_id: UUID,
    request: UpdateStageRequest,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageResponse]:
    """Update a Genesis stage record."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Updating Genesis stage {stage_id}")

        # Use appropriate service method based on status
        if request.status == StageStatus.COMPLETED:
            updated_stage = await stage_service.complete_stage(
                db=db,
                stage_id=stage_id,
                result=request.result,
                metrics=request.metrics,
            )
        elif request.status == StageStatus.FAILED:
            updated_stage = await stage_service.fail_stage(
                db=db,
                stage_id=stage_id,
                error_info=request.result,
            )
        elif request.config is not None:
            updated_stage = await stage_service.update_stage_config(
                db=db,
                stage_id=stage_id,
                config=request.config,
            )
        else:
            # Generic update for other cases
            updated_stage = await stage_service.get_stage(db, stage_id)
            if not updated_stage:
                raise HTTPException(status_code=404, detail="Genesis stage not found")

        if not updated_stage:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        data = StageResponse.from_orm(updated_stage)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stage updated successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in update_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update Genesis stage")


@router.post(
    "/stages/{stage_id}/increment-iteration",
    response_model=ApiResponse[StageResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def increment_stage_iteration(
    stage_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageResponse]:
    """Increment the iteration count for a Genesis stage."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Incrementing iteration for Genesis stage {stage_id}")

        updated_stage = await stage_service.increment_iteration(db=db, stage_id=stage_id)
        if not updated_stage:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        data = StageResponse.from_orm(updated_stage)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stage iteration incremented successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in increment_stage_iteration endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to increment Genesis stage iteration")


@router.get(
    "/stages",
    response_model=ApiResponse[list[StageResponse]],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_stages(
    response: Response,
    flow_id: UUID | None = Query(None, description="Filter by flow ID"),
    stage_type: GenesisStage | None = Query(None, alias="stage", description="Filter by stage type"),
    status_filter: StageStatus | None = Query(None, alias="status", description="Filter by stage status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of stages to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[StageResponse]]:
    """List Genesis stage records with optional filtering."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Listing Genesis stages with flow_id={flow_id}, stage={stage_type}, status={status_filter}")

        if flow_id:
            stages = await stage_service.list_stages_by_flow(
                db=db,
                flow_id=flow_id,
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        elif stage_type:
            stages = await stage_service.list_stages_by_type(
                db=db,
                stage=stage_type,
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        else:
            raise HTTPException(status_code=400, detail="Either flow_id or stage parameter is required")

        data = [StageResponse.from_orm(stage) for stage in stages]
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis stages retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in list_stages endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Genesis stages")


@router.delete(
    "/stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_stage(
    stage_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a Genesis stage record."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Deleting Genesis stage {stage_id}")

        deleted = await stage_service.delete_stage(db, stage_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        set_common_headers(response, correlation_id=corr_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in delete_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete Genesis stage")