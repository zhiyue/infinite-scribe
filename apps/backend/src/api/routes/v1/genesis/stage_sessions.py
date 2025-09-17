"""Genesis stage session association management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.genesis import GenesisStageSessionService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import StageSessionStatus
from src.schemas.genesis import CreateStageSessionRequest, StageSessionResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Service instance
stage_session_service = GenesisStageSessionService()


@router.post(
    "/stages/{stage_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[tuple[UUID, StageSessionResponse]],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_stage_session(
    stage_id: UUID,
    request: CreateStageSessionRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[tuple[UUID, StageSessionResponse]]:
    """Create and bind a new session to a stage, or bind an existing session."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Creating stage session association for stage {stage_id}")

        if request.session_id:
            # Bind existing session
            stage_session = await stage_session_service.bind_existing_session(
                db=db,
                stage_id=stage_id,
                session_id=request.session_id,
                novel_id=request.novel_id,
                is_primary=request.is_primary,
                session_kind=request.session_kind,
            )
            if not stage_session:
                raise HTTPException(status_code=400, detail="Invalid session or scope validation failed")

            session_id = request.session_id
        else:
            # Create new session and bind it
            session_id, stage_session = await stage_session_service.create_and_bind_session(
                db=db,
                stage_id=stage_id,
                novel_id=request.novel_id,
                is_primary=request.is_primary,
                session_kind=request.session_kind,
            )

        data = (session_id, StageSessionResponse.from_orm(stage_session))
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Stage session association created successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in create_stage_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stage session association") from None


@router.get(
    "/stages/{stage_id}/sessions",
    response_model=ApiResponse[list[StageSessionResponse]],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_stage_sessions(
    stage_id: UUID,
    response: Response,
    status_filter: StageSessionStatus | None = Query(None, alias="status", description="Filter by association status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of associations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[StageSessionResponse]]:
    """List all sessions associated with a stage."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Listing sessions for stage {stage_id}")

        associations = await stage_session_service.list_stage_sessions(
            db=db,
            stage_id=stage_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        data = [StageSessionResponse.from_orm(association) for association in associations]
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Stage sessions retrieved successfully", data=data)

    except Exception as e:
        logger.exception(f"Unexpected error in list_stage_sessions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to list stage sessions") from None
