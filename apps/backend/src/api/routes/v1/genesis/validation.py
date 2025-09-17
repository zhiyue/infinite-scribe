"""Validation functions for Genesis stage endpoints."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.flow.genesis_flow_service import GenesisFlowService
from src.common.services.genesis.stage.genesis_stage_service import GenesisStageService
from src.models.user import User


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


async def validate_stage_ownership(
    stage_id: UUID,
    user: User,
    stage_service: GenesisStageService,
    flow_service: GenesisFlowService,
    novel_service: NovelService,
) -> None:
    """Validate that the user owns the novel associated with the specified stage."""
    # Get the stage to find its flow_id
    stage = await stage_service.get_stage_by_id(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Genesis stage not found")

    # Get the flow to find its novel_id
    flow = await flow_service.get_flow_by_id(stage.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Genesis flow not found")

    # Validate novel ownership
    await validate_novel_ownership(flow.novel_id, user, novel_service, flow_service.db_session)