"""Genesis API路由

提供Genesis阶段解耦后的API端点。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.genesis import (
    GenesisFlowCreateRequest,
    GenesisFlowResponse,
    GenesisFlowUpdateRequest,
    GenesisFlowWithStagesResponse,
    GenesisStageCreateRequest,
    GenesisStageResponse,
    GenesisStageSessionCreateRequest,
    GenesisStageSessionResponse,
    GenesisStageSessionUpdateRequest,
    GenesisStageUpdateRequest,
    GenesisStageWithSessionsResponse,
    PaginatedGenesisFlowsResponse,
    PaginatedGenesisStagesResponse,
)
from src.common.repositories.genesis.flow_repository import SqlAlchemyGenesisFlowRepository
from src.common.repositories.genesis.stage_repository import SqlAlchemyGenesisStageRepository
from src.common.repositories.genesis.stage_session_repository import SqlAlchemyGenesisStageSessionRepository
from src.common.repositories.conversation.session_repository import SqlAlchemyConversationSessionRepository
from src.common.services.genesis.flow import GenesisFlowService
from src.common.services.genesis.stage import GenesisStageService
from src.common.services.genesis.session_binding import BindingValidationService
from src.database import get_db_session
from src.schemas.enums import GenesisStatus, GenesisStage, StageStatus, StageSessionStatus

router = APIRouter(prefix="/genesis", tags=["genesis"])


# Dependency functions
def get_genesis_flow_service(db: AsyncSession = Depends(get_db_session)) -> GenesisFlowService:
    """获取Genesis流程服务依赖"""
    flow_repo = SqlAlchemyGenesisFlowRepository(db)
    return GenesisFlowService(flow_repo, db)


def get_genesis_stage_service(db: AsyncSession = Depends(get_db_session)) -> GenesisStageService:
    """获取Genesis阶段服务依赖"""
    flow_repo = SqlAlchemyGenesisFlowRepository(db)
    stage_repo = SqlAlchemyGenesisStageRepository(db)
    stage_session_repo = SqlAlchemyGenesisStageSessionRepository(db)
    conversation_session_repo = SqlAlchemyConversationSessionRepository(db)

    return GenesisStageService(
        flow_repo,
        stage_repo,
        stage_session_repo,
        conversation_session_repo,
        db,
    )


def get_binding_validation_service(db: AsyncSession = Depends(get_db_session)) -> BindingValidationService:
    """获取绑定验证服务依赖"""
    flow_repo = SqlAlchemyGenesisFlowRepository(db)
    conversation_session_repo = SqlAlchemyConversationSessionRepository(db)
    return BindingValidationService(flow_repo, conversation_session_repo)


# Genesis Flow 端点
@router.post(
    "/flows/{novel_id}",
    response_model=GenesisFlowResponse,
    status_code=status.HTTP_200_OK,
    summary="创建或获取Genesis流程",
    description="幂等创建或返回指定小说的当前Genesis流程",
)
async def ensure_genesis_flow(
    novel_id: UUID,
    request: GenesisFlowCreateRequest | None = None,
    flow_service: GenesisFlowService = Depends(get_genesis_flow_service),
) -> GenesisFlowResponse:
    """确保Genesis流程存在，如果不存在则创建"""
    try:
        flow = await flow_service.ensure_flow(novel_id)
        return GenesisFlowResponse.model_validate(flow)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ensure Genesis flow: {str(e)}",
        )


@router.get(
    "/flows/{novel_id}",
    response_model=GenesisFlowWithStagesResponse,
    summary="获取Genesis流程详情",
    description="查看指定小说的Genesis流程进度与阶段摘要",
)
async def get_genesis_flow(
    novel_id: UUID,
    flow_service: GenesisFlowService = Depends(get_genesis_flow_service),
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> GenesisFlowWithStagesResponse:
    """获取Genesis流程及其阶段信息"""
    flow = await flow_service.get_flow(novel_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Genesis flow found for novel {novel_id}",
        )

    stages = await stage_service.list_stages_by_flow(flow.id)

    return GenesisFlowWithStagesResponse(
        flow=GenesisFlowResponse.model_validate(flow),
        stages=[GenesisStageResponse.model_validate(stage) for stage in stages],
    )


@router.put(
    "/flows/{novel_id}",
    response_model=GenesisFlowResponse,
    summary="更新Genesis流程",
    description="更新Genesis流程状态或阶段",
)
async def update_genesis_flow(
    novel_id: UUID,
    request: GenesisFlowUpdateRequest,
    flow_service: GenesisFlowService = Depends(get_genesis_flow_service),
) -> GenesisFlowResponse:
    """更新Genesis流程"""
    # 先获取当前流程
    flow = await flow_service.get_flow(novel_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Genesis flow found for novel {novel_id}",
        )

    # 根据请求类型执行不同的更新操作
    if request.status == GenesisStatus.COMPLETED:
        updated_flow = await flow_service.complete_flow(
            flow_id=flow.id,
            expected_version=request.expected_version,
            final_state=request.state,
        )
    elif request.status == GenesisStatus.PAUSED:
        updated_flow = await flow_service.pause_flow(
            flow_id=flow.id,
            expected_version=request.expected_version,
            pause_reason=request.state.get("pause_reason") if request.state else None,
        )
    elif request.status == GenesisStatus.ABANDONED:
        updated_flow = await flow_service.abandon_flow(
            flow_id=flow.id,
            expected_version=request.expected_version,
            abandon_reason=request.state.get("abandon_reason") if request.state else None,
        )
    elif request.current_stage:
        updated_flow = await flow_service.advance_stage(
            flow_id=flow.id,
            next_stage=request.current_stage,
            expected_version=request.expected_version,
            state_updates=request.state,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid update operation specified",
        )

    if not updated_flow:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to version conflict or flow not found",
        )

    return GenesisFlowResponse.model_validate(updated_flow)


# Genesis Stage 端点
@router.post(
    "/flows/{novel_id}/stages/{stage}",
    response_model=GenesisStageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建Genesis阶段",
    description="为指定流程创建新的阶段记录",
)
async def create_genesis_stage(
    novel_id: UUID,
    stage: GenesisStage,
    request: GenesisStageCreateRequest,
    flow_service: GenesisFlowService = Depends(get_genesis_flow_service),
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> GenesisStageResponse:
    """创建新的Genesis阶段"""
    # 获取流程
    flow = await flow_service.get_flow(novel_id)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Genesis flow found for novel {novel_id}",
        )

    try:
        stage_record = await stage_service.create_stage(
            flow_id=flow.id,
            stage=stage,
            config=request.config,
        )
        return GenesisStageResponse.model_validate(stage_record)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/stages/{stage_id}",
    response_model=GenesisStageWithSessionsResponse,
    summary="获取Genesis阶段详情",
    description="获取阶段信息及其关联的会话列表",
)
async def get_genesis_stage(
    stage_id: UUID,
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> GenesisStageWithSessionsResponse:
    """获取Genesis阶段及其会话信息"""
    stage = await stage_service.get_stage_by_id(stage_id)
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stage with ID {stage_id} not found",
        )

    sessions = await stage_service.list_stage_sessions(stage_id)

    return GenesisStageWithSessionsResponse(
        stage=GenesisStageResponse.model_validate(stage),
        sessions=[GenesisStageSessionResponse.model_validate(session) for session in sessions],
    )


@router.put(
    "/stages/{stage_id}",
    response_model=GenesisStageResponse,
    summary="更新Genesis阶段",
    description="更新阶段状态、配置或结果",
)
async def update_genesis_stage(
    stage_id: UUID,
    request: GenesisStageUpdateRequest,
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> GenesisStageResponse:
    """更新Genesis阶段"""
    if request.status == StageStatus.COMPLETED:
        updated_stage = await stage_service.complete_stage(
            stage_id=stage_id,
            result=request.result,
            metrics=request.metrics,
        )
    else:
        # 这里需要通过仓储直接更新，因为服务层还没有通用的update方法
        # 在实际实现中应该在GenesisStageService中添加通用的update方法
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="General stage update not implemented yet",
        )

    if not updated_stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stage with ID {stage_id} not found",
        )

    return GenesisStageResponse.model_validate(updated_stage)


# Genesis Stage Session 端点
@router.post(
    "/stages/{stage_id}/sessions",
    response_model=GenesisStageSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建阶段会话关联",
    description="创建新会话并绑定到阶段，或绑定现有会话",
)
async def create_stage_session(
    stage_id: UUID,
    request: GenesisStageSessionCreateRequest,
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
    flow_service: GenesisFlowService = Depends(get_genesis_flow_service),
    validation_service: BindingValidationService = Depends(get_binding_validation_service),
) -> GenesisStageSessionResponse:
    """创建阶段会话关联"""
    try:
        if request.session_id:
            # 绑定现有会话
            association = await stage_service.add_stage_session(
                stage_id=stage_id,
                session_id=request.session_id,
                is_primary=request.is_primary,
                session_kind=request.session_kind,
            )
        else:
            # 创建新会话并绑定
            # 需要先获取阶段信息来确定novel_id
            stage = await stage_service.get_stage_by_id(stage_id)
            if not stage:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stage with ID {stage_id} not found",
                )

            # 通过流程获取novel_id
            flow = await flow_service.get_flow_by_id(stage.flow_id)
            if not flow:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Flow with ID {stage.flow_id} not found",
                )

            session_id = await stage_service.create_and_bind_session(
                stage_id=stage_id,
                novel_id=flow.novel_id,
                is_primary=request.is_primary,
                session_kind=request.session_kind,
            )

            # 获取创建的关联
            associations = await stage_service.list_stage_sessions(stage_id)
            association = next((a for a in associations if a.session_id == session_id), None)
            if not association:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve created association",
                )

        return GenesisStageSessionResponse.model_validate(association)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/stages/{stage_id}/sessions",
    response_model=list[GenesisStageSessionResponse],
    summary="列出阶段会话",
    description="列出指定阶段的所有会话关联",
)
async def list_stage_sessions(
    stage_id: UUID,
    status: Annotated[StageSessionStatus | None, Query(description="按状态过滤")] = None,
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> list[GenesisStageSessionResponse]:
    """列出阶段的会话关联"""
    sessions = await stage_service.list_stage_sessions(stage_id, status)
    return [GenesisStageSessionResponse.model_validate(session) for session in sessions]


@router.put(
    "/stages/{stage_id}/sessions/{session_id}/primary",
    response_model=GenesisStageSessionResponse,
    summary="设置主会话",
    description="将指定会话设为阶段的主会话",
)
async def set_primary_session(
    stage_id: UUID,
    session_id: UUID,
    stage_service: GenesisStageService = Depends(get_genesis_stage_service),
) -> GenesisStageSessionResponse:
    """设置主会话"""
    association = await stage_service.set_primary_session(stage_id, session_id)
    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Association not found for stage {stage_id} and session {session_id}",
        )

    return GenesisStageSessionResponse.model_validate(association)


# 查询端点
@router.get(
    "/flows",
    response_model=PaginatedGenesisFlowsResponse,
    summary="列出Genesis流程",
    description="按状态列出Genesis流程",
)
async def list_genesis_flows(
    status: Annotated[GenesisStatus, Query(description="流程状态")],
    limit: Annotated[int, Query(description="返回数量限制", ge=1, le=100)] = 50,
    offset: Annotated[int, Query(description="偏移量", ge=0)] = 0,
    flow_service: GenesisFlowService = Depends(get_genesis_flow_service),
) -> PaginatedGenesisFlowsResponse:
    """列出Genesis流程"""
    flows = await flow_service.list_flows_by_status(status, limit, offset)
    return PaginatedGenesisFlowsResponse(
        flows=[GenesisFlowResponse.model_validate(flow) for flow in flows],
        total=len(flows),  # 实际应该是总数查询
        offset=offset,
        limit=limit,
    )