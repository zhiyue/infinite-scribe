"""Dependency injection functions for Genesis stage endpoints."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation.session_repository import SqlAlchemyConversationSessionRepository
from src.common.repositories.genesis.flow_repository import SqlAlchemyGenesisFlowRepository
from src.common.repositories.genesis.stage_repository import SqlAlchemyGenesisStageRepository
from src.common.repositories.genesis.stage_session_repository import SqlAlchemyGenesisStageSessionRepository
from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.flow.genesis_flow_service import GenesisFlowService
from src.common.services.genesis.stage.genesis_stage_service import GenesisStageService
from src.database import get_db


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
