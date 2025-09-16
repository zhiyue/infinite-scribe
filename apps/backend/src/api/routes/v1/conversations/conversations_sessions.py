"""Session management endpoints for conversations."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.conversation.conversation_service import conversation_service
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.common.utils.datetime_utils import format_iso_datetime, utc_now
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.novel.dialogue import (
    CreateSessionRequest,
    ScopeType,
    SessionResponse,
    SessionStatus,
    UpdateSessionRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[SessionResponse],
    responses=COMMON_ERROR_RESPONSES,
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
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(
            f"Creating session for user {current_user.id}, scope_type={request.scope_type}, scope_id={request.scope_id}"
        )

        result = await conversation_service.create_session(
            db,
            current_user.id,
            request.scope_type,
            request.scope_id,
            stage=request.stage,
            initial_state=request.initial_state,
        )

        logger.info(f"Service result: {result}")

        if not result.get("success"):
            code = result.get("code", 422)
            error_msg = result.get("error", "Failed to create session")
            logger.error(f"Service returned error: code={code}, error={error_msg}")
            raise HTTPException(status_code=code, detail=error_msg)

    except Exception as e:
        logger.exception(f"Unexpected error in create_session endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

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
            created_at=s.get("created_at") or format_iso_datetime(utc_now()),
            updated_at=s.get("updated_at") or format_iso_datetime(utc_now()),
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
            created_at=s.created_at.isoformat() if getattr(s, "created_at", None) else format_iso_datetime(utc_now()),
            updated_at=s.updated_at.isoformat() if getattr(s, "updated_at", None) else format_iso_datetime(utc_now()),
            novel_id=None,
        )
    set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
    return ApiResponse(code=0, msg="创建会话成功", data=data)


@router.get(
    "/sessions",
    response_model=ApiResponse[list[SessionResponse]],
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_sessions(
    response: Response,
    scope_type: str = Query(..., description="Scope type (e.g., 'GENESIS')"),
    scope_id: str = Query(..., description="Scope identifier (e.g., novel ID)"),
    status: str | None = Query(None, description="Optional status filter"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of sessions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(require_auth),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SessionResponse]]:
    """List conversation sessions for a given scope (e.g., novel ID)."""
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        logger.info(
            f"Listing sessions for user {current_user.id}, scope_type={scope_type}, scope_id={scope_id}, status={status}"
        )

        result = await conversation_service.list_sessions(
            db,
            current_user.id,
            scope_type=scope_type,
            scope_id=scope_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        logger.info(f"Service result: {result}")

        if not result.get("success"):
            code = result.get("code", 422)
            error_msg = result.get("error", "Failed to list sessions")
            logger.error(f"Service returned error: code={code}, error={error_msg}")
            raise HTTPException(status_code=code, detail=error_msg)

    except Exception as e:
        logger.exception(f"Unexpected error in list_sessions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to list sessions")

    sessions_data = result["sessions"]
    # Convert sessions to response format
    sessions_list = []
    for s in sessions_data:
        if isinstance(s, dict):
            version = s.get("version", 1)
            session_response = SessionResponse(
                id=UUID(s["id"]) if isinstance(s["id"], str) else s["id"],
                scope_type=ScopeType(s["scope_type"]),
                scope_id=s["scope_id"],
                status=SessionStatus(s["status"]),
                stage=s.get("stage"),
                state=s.get("state", {}),
                version=version,
                created_at=s.get("created_at") or format_iso_datetime(utc_now()),
                updated_at=s.get("updated_at") or format_iso_datetime(utc_now()),
                novel_id=None,
            )
        else:
            version = getattr(s, "version", 1)
            session_response = SessionResponse(
                id=s.id,
                scope_type=ScopeType(s.scope_type),
                scope_id=s.scope_id,
                status=SessionStatus(s.status),
                stage=s.stage,
                state=s.state or {},
                version=version,
                created_at=s.created_at.isoformat()
                if getattr(s, "created_at", None)
                else format_iso_datetime(utc_now()),
                updated_at=s.updated_at.isoformat()
                if getattr(s, "updated_at", None)
                else format_iso_datetime(utc_now()),
                novel_id=None,
            )
        sessions_list.append(session_response)

    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取会话列表成功", data=sessions_list)


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
    corr_id = get_or_create_correlation_id(x_correlation_id)
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
            created_at=s.get("created_at") or format_iso_datetime(utc_now()),
            updated_at=s.get("updated_at") or format_iso_datetime(utc_now()),
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
            created_at=s.created_at.isoformat() if getattr(s, "created_at", None) else format_iso_datetime(utc_now()),
            updated_at=s.updated_at.isoformat() if getattr(s, "updated_at", None) else format_iso_datetime(utc_now()),
            novel_id=None,
        )
    set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
    return ApiResponse(code=0, msg="获取会话成功", data=data)


@router.patch(
    "/sessions/{session_id}",
    response_model=ApiResponse[SessionResponse],
    responses=COMMON_ERROR_RESPONSES,
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
    try:
        corr_id = get_or_create_correlation_id(x_correlation_id)
        expected_version = None
        if if_match:
            try:
                expected_version = int(if_match.strip('"'))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid If-Match header") from None

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
        # Try to get serialized_session first, otherwise use session
        if "serialized_session" in result:
            s = result["serialized_session"]
            # serialized_session is already a dict
            data = SessionResponse(
                id=UUID(s["id"]) if isinstance(s["id"], str) else s["id"],
                scope_type=ScopeType(s["scope_type"]),
                scope_id=s["scope_id"],
                status=SessionStatus(s["status"]),
                stage=s.get("stage"),
                state=s.get("state", {}),
                version=s.get("version", 1),
                created_at=s.get("created_at") or format_iso_datetime(utc_now()),
                updated_at=s.get("updated_at") or format_iso_datetime(utc_now()),
                novel_id=None,
            )
        else:
            # Fall back to ORM object
            s = result["session"]
            data = SessionResponse(
                id=s.id,
                scope_type=ScopeType(s.scope_type),
                scope_id=s.scope_id,
                status=SessionStatus(s.status),
                stage=s.stage,
                state=s.state or {},
                version=s.version,
                created_at=s.created_at.isoformat()
                if getattr(s, "created_at", None)
                else format_iso_datetime(utc_now()),
                updated_at=s.updated_at.isoformat()
                if getattr(s, "updated_at", None)
                else format_iso_datetime(utc_now()),
                novel_id=None,
            )
        set_common_headers(response, correlation_id=corr_id, etag=f'"{data.version}"')
        return ApiResponse(code=0, msg="更新会话成功", data=data)
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        logger.error(f"Unexpected error in update_session endpoint: {e}\n{error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update session: {e!s}")


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
    corr_id = get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.delete_session(db, current_user.id, session_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Delete failed"))
    set_common_headers(response, correlation_id=corr_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
