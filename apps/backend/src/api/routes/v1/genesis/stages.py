"""Genesis stage record management endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.repositories.conversation.session_repository import SqlAlchemyConversationSessionRepository
from src.common.repositories.genesis.flow_repository import SqlAlchemyGenesisFlowRepository
from src.common.repositories.genesis.stage_repository import SqlAlchemyGenesisStageRepository
from src.common.repositories.genesis.stage_session_repository import SqlAlchemyGenesisStageSessionRepository
from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.flow.genesis_flow_service import GenesisFlowService
from src.common.services.genesis.stage.genesis_stage_service import GenesisStageService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import GenesisStage, StageStatus
from src.schemas.genesis import CreateStageRequest, StageResponse, UpdateStageRequest
from src.schemas.novel.dialogue import ConversationRoundResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Service dependency injection
async def get_genesis_stage_service(db: AsyncSession = Depends(get_db)) -> GenesisStageService:
    """Create GenesisStageService with proper dependency injection."""
    flow_repo = SqlAlchemyGenesisFlowRepository(db)
    stage_repo = SqlAlchemyGenesisStageRepository(db)
    stage_session_repo = SqlAlchemyGenesisStageSessionRepository(db)
    conversation_session_repo = SqlAlchemyConversationSessionRepository(db)
    return GenesisStageService(flow_repo, stage_repo, stage_session_repo, conversation_session_repo, db)


def get_novel_service() -> NovelService:
    """Dependency injection for NovelService."""
    return NovelService()


async def get_flow_service(db: AsyncSession = Depends(get_db)) -> GenesisFlowService:
    """Create GenesisFlowService with proper dependency injection."""
    flow_repository = SqlAlchemyGenesisFlowRepository(db)
    return GenesisFlowService(flow_repository, db_session=db)


async def validate_novel_ownership(
    novel_id: UUID,
    user: User,
    novel_service: NovelService,
    db: AsyncSession,
) -> None:
    """Validate that the user owns the specified novel."""
    result = await novel_service.get_novel(db, user.id, novel_id)
    if not result["success"]:
        if result["error"] == "Novel not found":
            raise HTTPException(status_code=404, detail="Novel not found or you don't have permission to access it")
        else:
            raise HTTPException(status_code=500, detail="Failed to validate novel ownership")


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
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[StageResponse]:
    """Get a Genesis stage record by ID."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis stage {stage_id}")

        stage_record = await stage_service.get_stage_by_id(stage_id)
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
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[StageResponse]:
    """Get the latest stage record for a specific flow and stage type."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting Genesis stage {stage} for flow {flow_id}")

        stage_record = await stage_service.get_stage_by_flow_and_stage(flow_id, stage)
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
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[StageResponse]:
    """Update a Genesis stage record."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Updating Genesis stage {stage_id}")

        # Use appropriate service method based on status
        if request.status == StageStatus.COMPLETED:
            updated_stage = await stage_service.complete_stage(
                stage_id=stage_id,
                result=request.result,
                metrics=request.metrics,
            )
        elif request.status == StageStatus.FAILED:
            updated_stage = await stage_service.fail_stage(
                stage_id=stage_id,
                error_info=request.result,
            )
        elif request.config is not None:
            updated_stage = await stage_service.update_stage_config(
                stage_id=stage_id,
                config=request.config,
            )
        else:
            # Generic update for other cases
            updated_stage = await stage_service.get_stage_by_id(stage_id)
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
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[StageResponse]:
    """Increment the iteration count for a Genesis stage."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Incrementing iteration for Genesis stage {stage_id}")

        updated_stage = await stage_service.increment_iteration(stage_id=stage_id)
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
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[list[StageResponse]]:
    """List Genesis stage records with optional filtering."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Listing Genesis stages with flow_id={flow_id}, stage={stage_type}, status={status_filter}")

        if flow_id:
            stages = await stage_service.list_stages_by_flow(
                flow_id=flow_id,
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        elif stage_type:
            stages = await stage_service.list_stages_by_type(
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
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
):
    """Delete a Genesis stage record."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Deleting Genesis stage {stage_id}")

        deleted = await stage_service.delete_stage(stage_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        set_common_headers(response, correlation_id=corr_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in delete_stage endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete Genesis stage")


@router.get(
    "/stages/{stage_id}/rounds",
    response_model=ApiResponse[list[ConversationRoundResponse]],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Get conversation rounds for Genesis stage",
    description="Retrieve all conversation rounds associated with a specific Genesis stage, ordered by creation time.",
)
async def get_stage_rounds(
    stage_id: UUID,
    response: Response,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of rounds to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> ApiResponse[list[ConversationRoundResponse]]:
    """Get all conversation rounds for a specific Genesis stage."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting conversation rounds for Genesis stage {stage_id}")

        # First verify the stage exists
        stage_record = await stage_service.get_stage_by_id(stage_id)
        if not stage_record:
            raise HTTPException(status_code=404, detail="Genesis stage not found")

        # Execute the SQL query from design document:
        # SELECT r.* FROM genesis_stage_sessions gss
        # JOIN conversation_rounds r ON r.session_id=gss.session_id
        # WHERE gss.stage_id=$1 ORDER BY r.created_at;
        query = text("""
            SELECT
                r.session_id,
                r.round_path,
                r.role,
                r.input,
                r.output,
                r.tool_calls,
                r.model,
                r.tokens_in,
                r.tokens_out,
                r.latency_ms,
                r.cost,
                r.correlation_id,
                r.created_at
            FROM genesis_stage_sessions gss
            JOIN conversation_rounds r ON r.session_id = gss.session_id
            WHERE gss.stage_id = :stage_id
            ORDER BY r.created_at
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(query, {"stage_id": stage_id, "limit": limit, "offset": offset})

        # Convert result to list of ConversationRoundResponse objects
        rounds = []
        for row in result:
            round_response = ConversationRoundResponse(
                session_id=row.session_id,
                round_path=row.round_path,
                role=row.role,
                input=row.input or {},
                output=row.output,
                tool_calls=row.tool_calls,
                model=row.model or "unknown",
                tokens_in=row.tokens_in,
                tokens_out=row.tokens_out,
                latency_ms=row.latency_ms,
                cost=row.cost,
                correlation_id=row.correlation_id,
                created_at=row.created_at,
            )
            rounds.append(round_response)

        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(code=0, msg=f"Retrieved {len(rounds)} conversation rounds for stage {stage_id}", data=rounds)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage_rounds endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stage conversation rounds")
