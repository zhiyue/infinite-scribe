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
from src.schemas.genesis import CreateStageSessionRequest, StageSessionResponse, UpdateStageSessionRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Service instance
stage_session_service = GenesisStageSessionService()


@router.post(
    "/stage-sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[tuple[UUID, StageSessionResponse]],
    responses=COMMON_ERROR_RESPONSES,
)
async def create_stage_session(
    request: CreateStageSessionRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[tuple[UUID, StageSessionResponse]]:
    """Create a new stage session association."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Creating stage session association for stage {request.stage_id}")

        if request.session_id:
            # Bind existing session
            stage_session = await stage_session_service.bind_existing_session(
                db=db,
                stage_id=request.stage_id,
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
                stage_id=request.stage_id,
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
        raise HTTPException(status_code=500, detail="Failed to create stage session association")


@router.get(
    "/stage-sessions/{association_id}",
    response_model=ApiResponse[StageSessionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_stage_session(
    association_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageSessionResponse]:
    """Get a stage session association by ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting stage session association {association_id}")

        association = await stage_session_service.get_association(db, association_id)
        if not association:
            raise HTTPException(status_code=404, detail="Stage session association not found")

        data = StageSessionResponse.from_orm(association)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Stage session association retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stage session association")


@router.get(
    "/stage-sessions/by-stage-and-session/{stage_id}/{session_id}",
    response_model=ApiResponse[StageSessionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_stage_session_by_ids(
    stage_id: UUID,
    session_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageSessionResponse]:
    """Get a stage session association by stage ID and session ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting stage session association for stage {stage_id} and session {session_id}")

        association = await stage_session_service.get_association_by_stage_and_session(db, stage_id, session_id)
        if not association:
            raise HTTPException(status_code=404, detail="Stage session association not found")

        data = StageSessionResponse.from_orm(association)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Stage session association retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage_session_by_ids endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stage session association")


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
        raise HTTPException(status_code=500, detail="Failed to list stage sessions")


@router.get(
    "/sessions/{session_id}/stages",
    response_model=ApiResponse[list[StageSessionResponse]],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_session_stages(
    session_id: UUID,
    response: Response,
    status_filter: StageSessionStatus | None = Query(None, alias="status", description="Filter by association status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of associations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[StageSessionResponse]]:
    """List all stages associated with a session."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Listing stages for session {session_id}")

        associations = await stage_session_service.list_session_stages(
            db=db,
            session_id=session_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        data = [StageSessionResponse.from_orm(association) for association in associations]
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Session stages retrieved successfully", data=data)

    except Exception as e:
        logger.exception(f"Unexpected error in list_session_stages endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to list session stages")


@router.get(
    "/stages/{stage_id}/primary-session",
    response_model=ApiResponse[StageSessionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_primary_session(
    stage_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageSessionResponse]:
    """Get the primary session for a stage."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting primary session for stage {stage_id}")

        association = await stage_session_service.get_primary_session(db, stage_id)
        if not association:
            raise HTTPException(status_code=404, detail="No primary session found for this stage")

        data = StageSessionResponse.from_orm(association)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Primary session retrieved successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_primary_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get primary session")


@router.post(
    "/stages/{stage_id}/set-primary-session/{session_id}",
    response_model=ApiResponse[StageSessionResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def set_primary_session(
    stage_id: UUID,
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageSessionResponse]:
    """Set a session as primary for a stage."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Setting session {session_id} as primary for stage {stage_id}")

        updated_association = await stage_session_service.set_primary_session(db, stage_id, session_id)
        if not updated_association:
            raise HTTPException(status_code=404, detail="Stage or session not found")

        data = StageSessionResponse.from_orm(updated_association)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Primary session set successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in set_primary_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to set primary session")


@router.patch(
    "/stage-sessions/{association_id}",
    response_model=ApiResponse[StageSessionResponse],
    responses=COMMON_ERROR_RESPONSES,
)
async def update_stage_session(
    association_id: UUID,
    request: UpdateStageSessionRequest,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StageSessionResponse]:
    """Update a stage session association."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Updating stage session association {association_id}")

        # Use appropriate service method based on status
        if request.status == StageSessionStatus.ARCHIVED:
            updated_association = await stage_session_service.archive_session(db, association_id)
        elif request.status == StageSessionStatus.CLOSED:
            updated_association = await stage_session_service.close_session(db, association_id)
        elif request.session_kind is not None:
            updated_association = await stage_session_service.update_session_kind(
                db, association_id, request.session_kind
            )
        else:
            # Generic update for other cases
            updated_association = await stage_session_service.get_association(db, association_id)

        if not updated_association:
            raise HTTPException(status_code=404, detail="Stage session association not found")

        data = StageSessionResponse.from_orm(updated_association)
        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg="Stage session association updated successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in update_stage_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update stage session association")


@router.delete(
    "/stage-sessions/{association_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_stage_session(
    association_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a stage session association."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Deleting stage session association {association_id}")

        deleted = await stage_session_service.delete_association(db, association_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Stage session association not found")

        set_common_headers(response, correlation_id=corr_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in delete_stage_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete stage session association")