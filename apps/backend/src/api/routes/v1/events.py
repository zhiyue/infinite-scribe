"""SSE (Server-Sent Events) API endpoints."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.routes.v1.auth_sse_token import verify_sse_token
from src.services.sse import RedisSSEService, SSEConnectionManager
from src.services.sse.provider import SSEProvider, get_default_provider

logger = logging.getLogger(__name__)

router = APIRouter()


# Configuration constants
SSE_SERVICE_VERSION = "1.0.0"
HEALTH_CHECK_TIMEOUT = 5.0


class ConnectionStatistics(BaseModel):
    """SSE connection statistics model."""

    active_connections: int
    redis_connection_counters: int


class SSEHealthResponse(BaseModel):
    """SSE health check response model."""

    status: str
    redis_status: str
    connection_statistics: ConnectionStatistics
    service: str
    version: str


async def get_redis_sse_service(request: Request) -> RedisSSEService:
    """Resolve Redis SSE service via provider.

    Prefers app-scoped provider (`app.state.sse_provider`),
    falls back to process default provider for non-web contexts.
    """
    provider: SSEProvider | None = getattr(request.app.state, "sse_provider", None)
    if provider is None:
        provider = get_default_provider()
    return await provider.get_redis_sse_service()


async def get_sse_connection_manager(
    request: Request,
    redis_sse_service: RedisSSEService = Depends(get_redis_sse_service),
) -> SSEConnectionManager:
    """Resolve SSE connection manager via provider."""
    provider: SSEProvider | None = getattr(request.app.state, "sse_provider", None)
    if provider is None:
        provider = get_default_provider()
    return await provider.get_connection_manager()


@router.get("/stream")
async def sse_stream(
    request: Request,
    sse_token: Annotated[str, Query(description="SSE authentication token")],
    preflight: Annotated[bool, Query(description="Preflight check only (no stream)")] = False,
    sse_connection_manager: SSEConnectionManager = Depends(get_sse_connection_manager),
):
    """SSE streaming endpoint for real-time events."""
    logger.info(
        "🌟 SSE stream endpoint accessed",
        extra={
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "has_sse_token": bool(sse_token),
            "last_event_id": request.headers.get("last-event-id"),
            "endpoint": "/api/v1/events/stream",
        },
    )

    try:
        # 验证SSE token并获取用户ID
        logger.debug("🔐 开始验证SSE token")
        user_id = verify_sse_token(sse_token)
        logger.info(
            "✅ SSE token验证成功",
            extra={"user_id": user_id, "client_host": request.client.host if request.client else "unknown"},
        )

        # 预检模式：仅进行连接数限制检查，不建立SSE流
        if preflight:
            from src.services.sse.config import sse_config

            logger.info(
                "🧪 SSE预检请求（不建立流）",
                extra={
                    "user_id": user_id,
                    "endpoint": "/api/v1/events/stream",
                    "preflight": True,
                },
            )

            try:
                # 读取当前用户的连接计数（不自增）
                conn_count = 0
                counter_service = getattr(sse_connection_manager, "redis_counter_service", None)
                if counter_service and hasattr(counter_service, "get_user_connection_count"):
                    conn_count = await counter_service.get_user_connection_count(str(user_id))

                if conn_count >= sse_config.MAX_CONNECTIONS_PER_USER:
                    logger.warning(
                        "⛔ 预检失败：用户连接数已达上限",
                        extra={
                            "user_id": user_id,
                            "conn_count": conn_count,
                            "limit": sse_config.MAX_CONNECTIONS_PER_USER,
                        },
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "status": "too_many_connections",
                            "message": "Too many concurrent SSE connections",
                            "current": conn_count,
                            "limit": sse_config.MAX_CONNECTIONS_PER_USER,
                        },
                        headers={"Retry-After": str(sse_config.RETRY_AFTER_SECONDS)},
                    )

                logger.info(
                    "✅ 预检通过：可建立SSE连接",
                    extra={"user_id": user_id, "conn_count": conn_count},
                )
                return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
            except Exception as e:
                logger.error(f"SSE预检失败: {e}")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"status": "unhealthy", "error": str(e)},
                )

        # 建立SSE连接
        logger.info("🔗 准备建立SSE连接", extra={"user_id": user_id, "endpoint": "/api/v1/events/stream"})

        response = await sse_connection_manager.add_connection(request, user_id)

        logger.info("🎉 SSE连接建立成功", extra={"user_id": user_id, "response_type": type(response).__name__})

        return response

    except HTTPException as e:
        logger.warning(
            f"SSE连接被拒绝: {e.detail}",
            extra={"status_code": e.status_code, "user_agent": request.headers.get("user-agent", "unknown")[:50]},
        )
        raise
    except Exception as e:
        logger.error(f"SSE连接失败: {type(e).__name__}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to establish SSE connection"
        ) from e


@router.get("/health", response_model=SSEHealthResponse)
async def sse_health(request: Request):
    """SSE service health check endpoint."""
    try:
        # Initialize services from app state (or lazy init)
        redis_sse_service = await get_redis_sse_service(request)
        sse_connection_manager = await get_sse_connection_manager(request, redis_sse_service)

        # Get connection statistics
        connection_stats = await _get_connection_stats(sse_connection_manager)

        # Check Redis health
        redis_healthy = await _check_redis_health(redis_sse_service)

        # Determine overall status
        overall_status = _determine_overall_status(redis_healthy, connection_stats)

        health_data = SSEHealthResponse(
            status=overall_status,
            redis_status="healthy" if redis_healthy else "unhealthy",
            connection_statistics=ConnectionStatistics(**connection_stats),
            service="sse",
            version=SSE_SERVICE_VERSION,
        )

        # Return appropriate status code
        if overall_status in ["unhealthy", "degraded"]:
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health_data.model_dump())

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_data = {"status": "unhealthy", "error": str(e), "service": "sse", "version": SSE_SERVICE_VERSION}
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=error_data)


async def _get_connection_stats(sse_connection_manager: SSEConnectionManager) -> dict:
    """Get connection statistics with timeout protection."""
    try:
        return await asyncio.wait_for(sse_connection_manager.get_connection_count(), timeout=HEALTH_CHECK_TIMEOUT)
    except (TimeoutError, Exception) as e:
        logger.warning(f"Failed to get connection statistics: {e}")
        return {"active_connections": -1, "redis_connection_counters": -1}


async def _check_redis_health(redis_sse_service: RedisSSEService) -> bool:
    """Check Redis connectivity with timeout protection using public method."""
    try:
        # Use public health check method instead of accessing private attributes
        return await asyncio.wait_for(redis_sse_service.check_health(), timeout=HEALTH_CHECK_TIMEOUT)
    except (TimeoutError, Exception) as e:
        logger.warning(f"Redis health check failed: {e}")
        return False


def _determine_overall_status(redis_healthy: bool, connection_stats: dict) -> str:
    """Determine overall service status based on components."""
    if connection_stats.get("active_connections", -1) == -1:
        return "unhealthy"  # Can't get basic stats

    # If Redis is not healthy, consider the service unhealthy
    # SSE service requires Redis for event publishing and connection management
    if not redis_healthy:
        return "unhealthy"

    return "healthy"


@router.post("/teardown")
async def sse_teardown(
    request: Request,
    sse_token: Annotated[str, Query(description="SSE authentication token")],
    tab_id: Annotated[str | None, Query(description="Browser tab id to teardown", alias="tab_id")] = None,
):
    """Teardown SSE connections for current user (optionally by tab).

    Allows front-end to proactively release server-side resources on page unload.
    """
    try:
        user_id = verify_sse_token(sse_token)
        provider: SSEProvider | None = getattr(request.app.state, "sse_provider", None)
        if provider is None:
            provider = get_default_provider()
        manager = await provider.get_connection_manager()

        if tab_id:
            existing = manager.state_manager.find_connection_by_tab(user_id, tab_id)
            if existing:
                conn_id, _ = existing
                await manager.state_manager.preempt_connection(conn_id, reason="teardown", free_slot_immediately=True)
        else:
            # Teardown all connections for this user
            for conn_id, _ in manager.state_manager.get_user_connections(user_id):  # type: ignore[attr-defined]
                await manager.state_manager.preempt_connection(conn_id, reason="teardown", free_slot_immediately=True)

        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    except Exception as e:
        logger.warning(f"SSE teardown failed: {e}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
