"""Genesis flow management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
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
from src.schemas.enums import GenesisStatus
from src.schemas.genesis import FlowResponse, UpdateFlowRequest

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.patch(
    "/flows/{flow_id}",
    response_model=ApiResponse[FlowResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def update_flow(
    flow_id: UUID,
    request: UpdateFlowRequest,
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    flow_service: GenesisFlowService = Depends(get_flow_service),
) -> ApiResponse[FlowResponse]:
    """Update a Genesis flow."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        expected_version = None
        if if_match:
            try:
                expected_version = int(if_match.strip('"'))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid If-Match header") from None

        logger.info(f"Updating Genesis flow {flow_id}")

        # TODO: Add flow ownership validation here

        # Use individual service methods based on what's being updated
        updated_flow = None
        if request.status is not None and request.status == GenesisStatus.COMPLETED:
            updated_flow = await flow_service.complete_flow(
                flow_id=flow_id,
                expected_version=expected_version,
            )
        elif request.current_stage is not None:
            updated_flow = await flow_service.advance_stage(
                flow_id=flow_id,
                next_stage=request.current_stage,
                expected_version=expected_version,
            )
        else:
            raise HTTPException(status_code=400, detail="No valid updates provided")

        if not updated_flow:
            raise HTTPException(status_code=409, detail="Version conflict or flow not found")

        # Commit transaction
        await flow_service.db_session.commit()

        data = FlowResponse.model_validate(updated_flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow updated successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        await flow_service.db_session.rollback()
        logger.exception(f"Unexpected error in update_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update Genesis flow") from None


@router.get(
    "/flows",
    response_model=ApiResponse[list[FlowResponse]],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_flows(
    response: Response,
    status_filter: GenesisStatus | None = Query(None, alias="status", description="Filter by flow status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of flows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    flow_service: GenesisFlowService = Depends(get_flow_service),
) -> ApiResponse[list[FlowResponse]]:
    """List Genesis flows with optional status filtering."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Listing Genesis flows with status={status_filter}")

        if status_filter:
            flows = await flow_service.list_flows_by_status(
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        else:
            # For now, default to listing IN_PROGRESS flows if no filter is provided
            flows = await flow_service.list_flows_by_status(
                status=GenesisStatus.IN_PROGRESS,
                limit=limit,
                offset=offset,
            )

        data = [FlowResponse.model_validate(flow) for flow in flows]
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis flows retrieved successfully", data=data)

    except Exception as e:
        logger.exception(f"Unexpected error in list_flows endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Genesis flows") from None


@router.delete(
    "/flows/{flow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_flow(
    flow_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    flow_service: GenesisFlowService = Depends(get_flow_service),
):
    """Delete a Genesis flow."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Deleting Genesis flow {flow_id}")

        # TODO: Add flow ownership validation here
        # TODO: Implement delete_flow method in service

        # For now, this is a placeholder - delete functionality needs to be implemented
        raise HTTPException(status_code=501, detail="Delete functionality not yet implemented")

        set_common_headers(response, correlation_id=corr_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in delete_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete Genesis flow") from None
