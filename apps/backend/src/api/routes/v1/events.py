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
    sse_connection_manager: SSEConnectionManager = Depends(get_sse_connection_manager),
):
    """SSE streaming endpoint for real-time events."""
    user_id = verify_sse_token(sse_token)

    try:
        return await sse_connection_manager.add_connection(request, user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error establishing SSE connection for user {user_id}: {e}")
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
