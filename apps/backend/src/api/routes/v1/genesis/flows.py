"""Genesis flow management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.genesis import GenesisFlowService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import GenesisStatus
from src.schemas.genesis import CreateFlowRequest, FlowResponse, UpdateFlowRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Service instance
flow_service = GenesisFlowService()


@router.post(
    "/flows",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[FlowResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_flow(
    request: CreateFlowRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FlowResponse]:
    """Create or ensure a Genesis flow exists for a novel."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Creating/ensuring Genesis flow for novel {request.novel_id}")

        # Use ensure_flow to create or return existing flow
        flow = await flow_service.ensure_flow(
            db=db,
            novel_id=request.novel_id,
            status=request.status,
            current_stage=request.current_stage,
        )

        # If state was provided in request, update it
        if request.state is not None:
            flow = await flow_service.update_flow_state(
                db=db,
                flow_id=flow.id,
                state=request.state,
                expected_version=flow.version,
            )

        data = FlowResponse.from_orm(flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow created/ensured successfully", data=data)

    except Exception as e:
        logger.exception(f"Unexpected error in create_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Genesis flow")


@router.get(
    "/flows/{flow_id}",
    response_model=ApiResponse[FlowResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_flow(
    flow_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FlowResponse]:
    """Get a Genesis flow by ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis flow {flow_id}")

        flow = await flow_service.get_flow(db, flow_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Genesis flow not found")

        data = FlowResponse.from_orm(flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Genesis flow")


@router.get(
    "/flows/by-novel/{novel_id}",
    response_model=ApiResponse[FlowResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_flow_by_novel(
    novel_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FlowResponse]:
    """Get a Genesis flow by novel ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis flow for novel {novel_id}")

        flow = await flow_service.get_flow_by_novel(db, novel_id)
        if not flow:
            raise HTTPException(status_code=404, detail="Genesis flow not found for this novel")

        data = FlowResponse.from_orm(flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_flow_by_novel endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Genesis flow")


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
    db: AsyncSession = Depends(get_db),
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

        # Use individual service methods based on what's being updated
        if request.status is not None and request.status == GenesisStatus.COMPLETED:
            updated_flow = await flow_service.complete_flow(
                db=db,
                flow_id=flow_id,
                expected_version=expected_version,
            )
        elif request.current_stage is not None:
            updated_flow = await flow_service.advance_stage(
                db=db,
                flow_id=flow_id,
                next_stage=request.current_stage,
                expected_version=expected_version,
            )
        elif request.state is not None:
            updated_flow = await flow_service.update_flow_state(
                db=db,
                flow_id=flow_id,
                state=request.state,
                expected_version=expected_version,
            )
        else:
            raise HTTPException(status_code=400, detail="No valid updates provided")

        if not updated_flow:
            raise HTTPException(status_code=409, detail="Version conflict or flow not found")

        data = FlowResponse.from_orm(updated_flow)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow updated successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in update_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update Genesis flow")


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
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[FlowResponse]]:
    """List Genesis flows with optional status filtering."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Listing Genesis flows with status={status_filter}")

        if status_filter:
            flows = await flow_service.list_flows_by_status(
                db=db,
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        else:
            # For now, default to listing IN_PROGRESS flows if no filter is provided
            flows = await flow_service.list_flows_by_status(
                db=db,
                status=GenesisStatus.IN_PROGRESS,
                limit=limit,
                offset=offset,
            )

        data = [FlowResponse.from_orm(flow) for flow in flows]
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Genesis flows retrieved successfully", data=data)

    except Exception as e:
        logger.exception(f"Unexpected error in list_flows endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Genesis flows")


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
    db: AsyncSession = Depends(get_db),
):
    """Delete a Genesis flow."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Deleting Genesis flow {flow_id}")

        deleted = await flow_service.delete_flow(db, flow_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Genesis flow not found")

        set_common_headers(response, correlation_id=corr_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in delete_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete Genesis flow")