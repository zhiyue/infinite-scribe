"""
Conversation (Genesis) endpoints skeleton.

This module provides a minimal, non-persistent skeleton of the unified
conversation API used to drive the Genesis flow (scope_type=GENESIS).

Semantics implemented:
- Headers: X-Correlation-Id passthrough/generation; Idempotency-Key optional capture
- ETag/If-Match: version echo (mocked) and 412 for mismatch when provided
- Status codes per LLD; responses use ApiResponse wrappers

Note: This is a stub for integration and contract validation. It does not
persist to database and should be replaced by real services.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.conversation_service import conversation_service
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.models.workflow import CommandInbox
from src.schemas.base import ApiResponse, PaginatedApiResponse, PaginatedResponse, PaginationInfo
from src.schemas.novel.dialogue import DialogueRole, ScopeType, SessionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Helpers ----------


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _get_or_create_correlation_id(x_corr_id: str | None) -> str:
    try:
        if x_corr_id and len(x_corr_id) <= 64:
            # Accept UUID-like or short ASCII strings
            return x_corr_id
    except Exception:
        pass
    return str(uuid4())


def _set_common_headers(resp: Response, correlation_id: str, etag: str | None = None, location: str | None = None):
    resp.headers["X-Correlation-Id"] = correlation_id
    if etag is not None:
        resp.headers["ETag"] = etag
    if location is not None:
        resp.headers["Location"] = location


# ---------- Local request/response models (route-scoped) ----------


class CreateSessionRequest(BaseModel):
    scope_type: ScopeType = Field(..., description="Type of dialogue scope", examples=["GENESIS"])
    scope_id: str = Field(..., description="Business entity ID, e.g., novel_id")
    stage: str | None = Field(None, description="Optional stage within scope")
    initial_state: dict[str, Any] | None = Field(default_factory=dict, description="Initial session state")


class SessionResponse(BaseModel):
    id: UUID
    scope_type: ScopeType
    scope_id: str
    status: SessionStatus
    stage: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    version: int
    created_at: str
    updated_at: str
    novel_id: UUID | None = None


class UpdateSessionRequest(BaseModel):
    status: SessionStatus | None = None
    stage: str | None = None
    state: dict[str, Any] | None = None


class RoundCreateRequest(BaseModel):
    role: DialogueRole = Field(..., description="Round role")
    input: dict[str, Any] = Field(..., description="Round input/prompt")
    model: str | None = Field(None, description="LLM model used")
    correlation_id: str | None = Field(None, description="Client-provided correlation id")


class RoundResponse(BaseModel):
    session_id: UUID
    round_path: str
    role: DialogueRole
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    model: str | None = None
    correlation_id: str | None = None
    created_at: str


class CommandRequest(BaseModel):
    type: str = Field(..., description="Command type")
    payload: dict[str, Any] | None = Field(default_factory=dict)


class CommandStatusResponse(BaseModel):
    command_id: UUID
    type: str
    status: str
    submitted_at: str
    correlation_id: str


class ContentSearchRequest(BaseModel):
    query: str | None = None
    stage: str | None = None
    type: str | None = None
    page: int = 1
    limit: int = 20


class VersionCreateRequest(BaseModel):
    base_version: int
    label: str
    description: str | None = None


class VersionMergeRequest(BaseModel):
    source: str
    target: str
    strategy: str | None = None


# ---------- Session management ----------


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[SessionResponse],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_session(
    request: CreateSessionRequest,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionResponse]:
    """Create a conversation session (scope=GENESIS)."""
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.create_session(
        db,
        current_user.id,
        request.scope_type,
        request.scope_id,
        stage=request.stage,
        initial_state=request.initial_state,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to create session"))

    s = result["session"]
    # s may be ORM or dict
    if isinstance(s, dict):
        version = s.get("version", 1)
        data = SessionResponse(
            id=UUID(s["id"]) if isinstance(s["id"], str) else s["id"],
            scope_type=ScopeType(s["scope_type"]),
            scope_id=s["scope_id"],
            status=SessionStatus(s["status"]),
            stage=s.get("stage"),
            state=s.get("state", {}),
            version=version,
            created_at=s.get("created_at") or _now_iso(),
            updated_at=s.get("updated_at") or _now_iso(),
            novel_id=None,
        )
    else:
        version = getattr(s, "version", 1)
        data = SessionResponse(
            id=s.id,
            scope_type=ScopeType(s.scope_type),
            scope_id=s.scope_id,
            status=SessionStatus(s.status),
            stage=s.stage,
            state=s.state or {},
            version=version,
            created_at=s.created_at.isoformat() if getattr(s, "created_at", None) else _now_iso(),
            updated_at=s.updated_at.isoformat() if getattr(s, "updated_at", None) else _now_iso(),
            novel_id=None,
        )
    _set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
    return ApiResponse(code=0, msg="创建会话成功", data=data)


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[SessionResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_session(
    session_id: UUID,
    response: Response,
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionResponse]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.get_session(db, current_user.id, session_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Session not found"))
    s = result["session"]
    if isinstance(s, dict):
        version = s.get("version", 1)
        data = SessionResponse(
            id=UUID(s["id"]) if isinstance(s["id"], str) else s["id"],
            scope_type=ScopeType(s["scope_type"]),
            scope_id=s["scope_id"],
            status=SessionStatus(s["status"]),
            stage=s.get("stage"),
            state=s.get("state", {}),
            version=version,
            created_at=s.get("created_at") or _now_iso(),
            updated_at=s.get("updated_at") or _now_iso(),
            novel_id=None,
        )
    else:
        version = getattr(s, "version", 1)
        data = SessionResponse(
            id=s.id,
            scope_type=ScopeType(s.scope_type),
            scope_id=s.scope_id,
            status=SessionStatus(s.status),
            stage=s.stage,
            state=s.state or {},
            version=version,
            created_at=s.created_at.isoformat() if getattr(s, "created_at", None) else _now_iso(),
            updated_at=s.updated_at.isoformat() if getattr(s, "updated_at", None) else _now_iso(),
            novel_id=None,
        )
    _set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
    return ApiResponse(code=0, msg="获取会话成功", data=data)


@router.patch(
    "/sessions/{session_id}",
    response_model=ApiResponse[SessionResponse],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        412: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def update_session(
    session_id: UUID,
    request: UpdateSessionRequest,
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SessionResponse]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    expected_version = None
    if if_match:
        try:
            expected_version = int(if_match.strip('"'))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid If-Match header")

    result = await conversation_service.update_session(
        db,
        current_user.id,
        session_id,
        status=request.status,
        stage=request.stage,
        state=request.state,
        expected_version=expected_version,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Update failed"))
    s = result["session"]
    data = SessionResponse(
        id=s.id,
        scope_type=ScopeType(s.scope_type),
        scope_id=s.scope_id,
        status=SessionStatus(s.status),
        stage=s.stage,
        state=s.state or {},
        version=s.version,
        created_at=s.created_at.isoformat() if getattr(s, "created_at", None) else _now_iso(),
        updated_at=s.updated_at.isoformat() if getattr(s, "updated_at", None) else _now_iso(),
        novel_id=None,
    )
    _set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
    return ApiResponse(code=0, msg="更新会话成功", data=data)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_session(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.delete_session(db, current_user.id, session_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Delete failed"))
    _set_common_headers(response, correlation_id=corr_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Rounds ----------


@router.get(
    "/sessions/{session_id}/rounds",
    response_model=PaginatedApiResponse[RoundResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def list_rounds(
    session_id: UUID,
    response: Response,
    after: str | None = Query(None, description="Cursor (round_path)"),
    limit: int = Query(50, ge=1, le=200),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    role: DialogueRole | None = Query(None),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PaginatedApiResponse[RoundResponse]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    _set_common_headers(response, correlation_id=corr_id)
    result = await conversation_service.list_rounds(
        db,
        current_user.id,
        session_id,
        after=after,
        limit=limit,
        order=order,
        role=role,
    )
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to list rounds"))
    rounds = result.get("rounds", [])
    items = [
        RoundResponse(
            session_id=r.session_id if hasattr(r, "session_id") else UUID(r["session_id"]),
            round_path=r.round_path if hasattr(r, "round_path") else r["round_path"],
            role=DialogueRole(r.role if hasattr(r, "role") else r["role"]),
            input=r.input if hasattr(r, "input") else r.get("input", {}),
            output=r.output if hasattr(r, "output") else r.get("output"),
            model=r.model if hasattr(r, "model") else r.get("model"),
            correlation_id=r.correlation_id if hasattr(r, "correlation_id") else r.get("correlation_id"),
            created_at=(r.created_at.isoformat() if hasattr(r, "created_at") else r.get("created_at") or _now_iso()),
        )
        for r in rounds
    ]
    pagination = PaginationInfo(page=1, page_size=limit, total=len(items), total_pages=1)
    return PaginatedApiResponse(code=0, msg="获取轮次成功", data=PaginatedResponse(items=items, pagination=pagination))


@router.post(
    "/sessions/{session_id}/rounds",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[RoundResponse],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def create_round(
    session_id: UUID,
    request: RoundCreateRequest,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RoundResponse]:
    corr_id = _get_or_create_correlation_id(request.correlation_id or x_correlation_id)
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
        created_at=(r.created_at.isoformat() if hasattr(r, "created_at") else r.get("created_at") or _now_iso()),
    )
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="创建轮次成功", data=data)


@router.get(
    "/sessions/{session_id}/rounds/{round_id}",
    response_model=ApiResponse[RoundResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_round(
    session_id: UUID,
    round_id: str = Path(..., description="Round path, e.g., 1 or 2.1"),
    response: Response | None = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RoundResponse]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    if response:
        _set_common_headers(response, correlation_id=corr_id)
    result = await conversation_service.get_round(db, current_user.id, session_id, round_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Round not found"))
    r = result["round"]
    data = RoundResponse(
        session_id=r["session_id"] if isinstance(r, dict) else r.session_id,
        round_path=r["round_path"] if isinstance(r, dict) else r.round_path,
        role=DialogueRole(r["role"] if isinstance(r, dict) else r.role),
        input=r.get("input", {}) if isinstance(r, dict) else r.input or {},
        output=r.get("output") if isinstance(r, dict) else r.output,
        model=r.get("model") if isinstance(r, dict) else r.model,
        correlation_id=r.get("correlation_id") if isinstance(r, dict) else r.correlation_id,
        created_at=(
            r.get("created_at")
            if isinstance(r, dict)
            else (r.created_at.isoformat() if getattr(r, "created_at", None) else _now_iso())
        ),
    )
    return ApiResponse(code=0, msg="获取轮次成功", data=data)


# ---------- Stage (Genesis-specific) ----------


@router.get(
    "/sessions/{session_id}/stage",
    response_model=ApiResponse[dict],
)
async def get_stage(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取阶段成功（skeleton）", data={"stage": "Stage_0"})


@router.put(
    "/sessions/{session_id}/stage",
    response_model=ApiResponse[dict],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        412: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def set_stage(
    session_id: UUID,
    stage: Annotated[str, Body(embed=True)],
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    if if_match is not None and if_match.strip('"') != "1":
        raise HTTPException(status_code=412, detail="Version mismatch (skeleton)")
    _set_common_headers(response, correlation_id=corr_id, etag='"2"')
    return ApiResponse(code=0, msg="切换阶段成功（skeleton）", data={"stage": stage, "version": 2})


@router.post(
    "/sessions/{session_id}/stage/validate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def validate_stage(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    cmd_id = uuid4()
    _set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="阶段验证已受理（skeleton）", data={"accepted": True, "command_id": str(cmd_id)})


@router.post(
    "/sessions/{session_id}/stage/lock",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def lock_stage(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    cmd_id = uuid4()
    _set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="阶段锁定已受理（skeleton）", data={"accepted": True, "command_id": str(cmd_id)})


# ---------- Messages & Commands ----------


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
    corr_id = _get_or_create_correlation_id(request.correlation_id or x_correlation_id)
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
        created_at=(r.created_at.isoformat() if hasattr(r, "created_at") else r.get("created_at") or _now_iso()),
    )
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="发送消息成功", data=data)


@router.post(
    "/sessions/{session_id}/commands",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
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
    corr_id = _get_or_create_correlation_id(x_correlation_id)
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
    _set_common_headers(
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
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    _set_common_headers(response, correlation_id=corr_id)
    # Fetch command status; ownership ensured via session in enqueue step; here we just show status if exists
    cmd = await db.scalar(select(CommandInbox).where(CommandInbox.id == cmd_id))
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    data = CommandStatusResponse(
        command_id=cmd_id,
        type=cmd.command_type,
        status=cmd.status.value if hasattr(cmd.status, "value") else str(cmd.status),
        submitted_at=(cmd.created_at.isoformat() if getattr(cmd, "created_at", None) else _now_iso()),
        correlation_id=corr_id,
    )
    return ApiResponse(code=0, msg="查询命令状态成功", data=data)


# ---------- Content ----------


@router.get(
    "/sessions/{session_id}/content",
    response_model=ApiResponse[dict],
)
async def get_content(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.get_session(db, current_user.id, session_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Session not found"))
    s = result["session"]
    state = s.get("state", {}) if isinstance(s, dict) else getattr(s, "state", {}) or {}
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取内容聚合成功", data={"state": state, "meta": {"updated_at": _now_iso()}})


@router.post(
    "/sessions/{session_id}/content/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def export_content(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.enqueue_command(
        db,
        current_user.id,
        session_id,
        command_type="CONTENT_EXPORT",
        payload={},
        idempotency_key=idempotency_key,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to enqueue export"))
    cmd = result["command"]
    cmd_id = getattr(cmd, "id", uuid4())
    _set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="导出任务已受理", data={"accepted": True, "command_id": str(cmd_id)})


@router.post(
    "/sessions/{session_id}/content/search",
    response_model=PaginatedApiResponse[dict],
)
async def search_content(
    session_id: UUID,
    request: ContentSearchRequest,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> PaginatedApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    _set_common_headers(response, correlation_id=corr_id)
    pagination = PaginationInfo(page=1, page_size=request.limit, total=0, total_pages=0)
    return PaginatedApiResponse(
        code=0, msg="搜索完成（skeleton）", data=PaginatedResponse(items=[], pagination=pagination)
    )


# ---------- Quality & Consistency ----------


@router.get(
    "/sessions/{session_id}/quality",
    response_model=ApiResponse[dict],
)
async def get_quality(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取质量评分（skeleton）", data={"score": 0.0, "updated_at": _now_iso()})


@router.post(
    "/sessions/{session_id}/consistency",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def trigger_consistency_check(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.enqueue_command(
        db,
        current_user.id,
        session_id,
        command_type="CONSISTENCY_CHECK",
        payload={},
        idempotency_key=idempotency_key,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to enqueue command"))
    cmd = result["command"]
    cmd_id = getattr(cmd, "id", uuid4())
    _set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="一致性检查已受理", data={"accepted": True, "command_id": str(cmd_id)})


# ---------- Versioning ----------


@router.get(
    "/sessions/{session_id}/versions",
    response_model=ApiResponse[list[dict]],
)
async def list_versions(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[list[dict]]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取版本列表（skeleton）", data=[])


@router.post(
    "/sessions/{session_id}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
)
async def create_version_branch(
    session_id: UUID,
    request: VersionCreateRequest,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    branch_id = f"v{request.base_version}-branch-{uuid4().hex[:8]}"
    _set_common_headers(
        response, correlation_id=corr_id, location=f"/api/v1/conversations/sessions/{session_id}/versions"
    )
    return ApiResponse(code=0, msg="创建分支成功（skeleton）", data={"branch": branch_id, "label": request.label})


@router.put(
    "/sessions/{session_id}/versions/merge",
    response_model=ApiResponse[dict],
)
async def merge_versions(
    session_id: UUID,
    request: VersionMergeRequest,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = _get_or_create_correlation_id(x_correlation_id)
    # For long-running merges, it could be 202. Here 200 to keep simple.
    _set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="合并完成（skeleton）", data={"target": request.target, "merged": True})
