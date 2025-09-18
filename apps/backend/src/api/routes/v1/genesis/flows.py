"""Genesis flow management endpoints."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.repositories.genesis.flow_repository import SqlAlchemyGenesisFlowRepository
from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.flow.genesis_flow_service import GenesisFlowService
from src.common.services.genesis.stage_service import GenesisStageService
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.enums import GenesisStage
from src.schemas.genesis import FlowResponse
from src.schemas.genesis.stage_config_schemas import (
    get_all_stage_config_schemas as get_all_schemas_dict,
)
from src.schemas.genesis.stage_config_schemas import (
    get_stage_config_example,
    get_stage_config_schema,
    validate_stage_config,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SwitchStageRequest(BaseModel):
    """阶段切换请求"""

    target_stage: GenesisStage


# Service dependency injection
async def get_flow_service(db: AsyncSession = Depends(get_db)) -> GenesisFlowService:
    """Create GenesisFlowService with proper dependency injection."""
    flow_repository = SqlAlchemyGenesisFlowRepository(db)
    from src.common.repositories.genesis.stage_repository import SqlAlchemyGenesisStageRepository

    stage_repository = SqlAlchemyGenesisStageRepository(db)

    # Add GenesisStageSessionService dependency
    from src.common.services.genesis.stage_session_service import GenesisStageSessionService

    stage_session_service = GenesisStageSessionService()

    return GenesisFlowService(flow_repository, db, stage_repository, stage_session_service)


async def get_novel_service() -> NovelService:
    """Create NovelService instance."""
    return NovelService()


async def get_stage_service(db: AsyncSession = Depends(get_db)) -> GenesisStageService:
    """Create GenesisStageService with proper dependency injection."""
    return GenesisStageService()


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

        # Get current stage ID
        current_stage_id = await flow_service.get_current_stage_id(flow)

        # Commit transaction
        await flow_service.db_session.commit()

        # Create response with current_stage_id
        flow_dict = flow.__dict__.copy()
        flow_dict["current_stage_id"] = current_stage_id
        data = FlowResponse.model_validate(flow_dict)
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

        # Get current stage ID
        current_stage_id = await flow_service.get_current_stage_id(flow)

        # Create response with current_stage_id
        flow_dict = flow.__dict__.copy()
        flow_dict["current_stage_id"] = current_stage_id
        data = FlowResponse.model_validate(flow_dict)
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
            raise HTTPException(status_code=409, detail="Failed to switch stage - invalid stage or flow not found")

        # Get current stage ID
        current_stage_id = await flow_service.get_current_stage_id(updated_flow)

        # Commit transaction
        await flow_service.db_session.commit()

        # Create response with current_stage_id
        flow_dict = updated_flow.__dict__.copy()
        flow_dict["current_stage_id"] = current_stage_id
        data = FlowResponse.model_validate(flow_dict)
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

        # Get current stage ID
        current_stage_id = await flow_service.get_current_stage_id(updated_flow)

        # Commit transaction
        await flow_service.db_session.commit()

        # Create response with current_stage_id
        flow_dict = updated_flow.__dict__.copy()
        flow_dict["current_stage_id"] = current_stage_id
        data = FlowResponse.model_validate(flow_dict)
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="Genesis flow completed successfully", data=data)

    except HTTPException:
        raise
    except Exception as e:
        await flow_service.db_session.rollback()
        logger.exception(f"Unexpected error in complete_flow endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete Genesis flow") from None


# Stage Configuration Endpoints
@router.get(
    "/stages/{stage}/config/schema",
    response_model=dict,
    responses=COMMON_ERROR_RESPONSES,
)
async def get_stage_config_schema_endpoint(
    stage: GenesisStage,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> dict:
    """Get the JSON Schema for a specific stage configuration."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting config schema for stage {stage.value}")

        # Get schema class for the stage
        schema_class = get_stage_config_schema(stage)
        schema_dict = schema_class.model_json_schema()

        set_common_headers(response, correlation_id=corr_id)
        return schema_dict

    except ValueError as e:
        logger.error(f"Invalid stage type {stage.value}: {e}")
        raise HTTPException(status_code=400, detail=f"Unsupported stage type: {stage.value}") from e
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage_config_schema endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stage config schema") from None


@router.get(
    "/stages/{stage}/config/template",
    response_model=dict,
    responses=COMMON_ERROR_RESPONSES,
)
async def get_stage_config_template_endpoint(
    stage: GenesisStage,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> dict:
    """Get the default template/example for a specific stage configuration."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Getting config template for stage {stage.value}")

        template_dict = get_stage_config_example(stage)

        set_common_headers(response, correlation_id=corr_id)
        return template_dict

    except ValueError as e:
        logger.error(f"Invalid stage type {stage.value}: {e}")
        raise HTTPException(status_code=400, detail=f"Unsupported stage type: {stage.value}") from e
    except Exception as e:
        logger.exception(f"Unexpected error in get_stage_config_template endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stage config template") from None


@router.get(
    "/stages/config/schemas",
    response_model=dict,
    responses=COMMON_ERROR_RESPONSES,
)
async def get_all_stage_config_schemas_endpoint(
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
) -> dict:
    """Get JSON Schemas for all stage configurations."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info("Getting config schemas for all stages")

        schemas = get_all_schemas_dict()

        set_common_headers(response, correlation_id=corr_id)
        return schemas

    except Exception as e:
        logger.exception(f"Unexpected error in get_all_stage_config_schemas endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to get all stage config schemas") from None


@router.patch(
    "/stages/{stage_id}/config",
    response_model=ApiResponse[dict],
    responses=COMMON_ERROR_RESPONSES,
)
async def update_stage_config_endpoint(
    stage_id: UUID,
    config_data: dict[str, Any],
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    stage_service: GenesisStageService = Depends(get_stage_service),
    flow_service: GenesisFlowService = Depends(get_flow_service),
    novel_service: NovelService = Depends(get_novel_service),
) -> ApiResponse[dict]:
    """Update configuration for a specific stage record."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(f"Updating config for stage {stage_id}")

        # Get the stage record to determine its type and validate ownership
        stage_record = await stage_service.get_stage(flow_service.db_session, stage_id)
        if not stage_record:
            raise HTTPException(status_code=404, detail="Stage record not found")

        # Validate flow ownership through the stage's flow
        await validate_flow_ownership(stage_record.flow_id, current_user, flow_service, novel_service)

        # Validate configuration against stage schema
        try:
            validated_config = validate_stage_config(stage_record.stage, config_data)
            normalized_config = validated_config.model_dump()
        except (ValidationError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid configuration for stage {stage_record.stage.value}: {exc!s}"
            ) from exc

        # Update the stage configuration
        updated_stage = await stage_service.update_stage_config(
            db=flow_service.db_session,
            stage_id=stage_id,
            config=normalized_config
        )

        if not updated_stage:
            raise HTTPException(status_code=500, detail="Failed to update stage configuration")

        # Return the updated configuration
        result_data = {
            "stage_id": str(updated_stage.id),
            "stage": updated_stage.stage.value,
            "config": updated_stage.config
        }

        set_common_headers(response, correlation_id=corr_id)
        return ApiResponse(
            code=0,
            msg="Stage configuration updated successfully",
            data=result_data
        )

    except HTTPException:
        raise
    except Exception as e:
        await flow_service.db_session.rollback()
        logger.exception(f"Unexpected error in update_stage_config endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to update stage configuration") from None
