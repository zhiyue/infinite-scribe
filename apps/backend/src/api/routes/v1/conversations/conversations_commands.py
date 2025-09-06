"""Messages & Commands endpoints for conversations."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation_service import conversation_service
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.common.utils.datetime_utils import format_iso_datetime, utc_now
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.models.workflow import CommandInbox
from src.schemas.base import ApiResponse
from src.schemas.novel.dialogue import (
    CommandRequest,
    CommandStatusResponse,
    DialogueRole,
    RoundCreateRequest,
    RoundResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ApiResponse[RoundResponse],
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    session_id: UUID,
    request: RoundCreateRequest,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RoundResponse]:
    # Alias to create_round with role defaulting to 'user' if not provided
    if not request.role:
        request.role = DialogueRole.USER
    corr_id = get_or_create_correlation_id(request.correlation_id or x_correlation_id)
    result = await conversation_service.create_round(
        db,
        current_user.id,
        session_id,
        role=request.role,
        input_data=request.input,
        model=request.model,
        correlation_id=corr_id,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to create round"))
    r = result["round"]
    data = RoundResponse(
        session_id=r.session_id if hasattr(r, "session_id") else UUID(r["session_id"]),
        round_path=r.round_path if hasattr(r, "round_path") else r["round_path"],
        role=DialogueRole(r.role if hasattr(r, "role") else r["role"]),
        input=r.input if hasattr(r, "input") else r.get("input", {}),
        output=r.output if hasattr(r, "output") else r.get("output"),
        model=r.model if hasattr(r, "model") else r.get("model"),
        correlation_id=r.correlation_id if hasattr(r, "correlation_id") else r.get("correlation_id"),
        created_at=(
            r.created_at.isoformat()
            if hasattr(r, "created_at")
            else r.get("created_at") or format_iso_datetime(utc_now())
        ),
    )
    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="发送消息成功", data=data)


@router.post(
    "/sessions/{session_id}/commands",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
    responses=COMMON_ERROR_RESPONSES,  # type: ignore[arg-type]
)
async def post_command(
    session_id: UUID,
    request: CommandRequest,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.enqueue_command(
        db,
        current_user.id,
        session_id,
        command_type=request.type,
        payload=request.payload or {},
        idempotency_key=idempotency_key,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to enqueue command"))
    cmd = result["command"]
    cmd_id = getattr(cmd, "id", uuid4())
    set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="命令已受理", data={"accepted": True, "command_id": str(cmd_id)})


@router.get(
    "/sessions/{session_id}/commands/{cmd_id}",
    response_model=ApiResponse[CommandStatusResponse],
)
async def get_command_status(
    session_id: UUID,
    cmd_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CommandStatusResponse]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    set_common_headers(response, correlation_id=corr_id)
    # Fetch command status; ownership ensured via session in enqueue step; here we just show status if exists
    cmd = await db.scalar(select(CommandInbox).where(CommandInbox.id == cmd_id))
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    data = CommandStatusResponse(
        command_id=cmd_id,
        type=cmd.command_type,
        status=cmd.status.value if hasattr(cmd.status, "value") else str(cmd.status),
        submitted_at=(
            cmd.created_at.isoformat() if getattr(cmd, "created_at", None) else format_iso_datetime(utc_now())  # type: ignore[attr-defined]
        ),
        correlation_id=corr_id,
    )
    return ApiResponse(code=0, msg="查询命令状态成功", data=data)
