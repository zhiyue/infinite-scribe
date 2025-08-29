"""SSE (Server-Sent Events) API endpoints."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.routes.v1.auth_sse_token import verify_sse_token
from src.common.services.redis_service import redis_service
from src.common.services.redis_sse_service import RedisSSEService
from src.services.sse_connection_manager import SSEConnectionManager

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


class SSEHealthErrorResponse(BaseModel):
    """SSE health check error response model."""

    status: str
    error: str
    service: str
    version: str


# Global SSE services - will be initialized on first use
_redis_sse_service: RedisSSEService | None = None
_sse_connection_manager: SSEConnectionManager | None = None

# Locks for thread-safe initialization
_redis_sse_service_lock = asyncio.Lock()
_sse_connection_manager_lock = asyncio.Lock()


async def get_redis_sse_service() -> RedisSSEService:
    """Get Redis SSE service with dependency injection."""
    global _redis_sse_service
    if _redis_sse_service is None:
        async with _redis_sse_service_lock:
            # Double-check pattern to prevent race conditions
            if _redis_sse_service is None:
                _redis_sse_service = RedisSSEService(redis_service)
                await _redis_sse_service.init_pubsub_client()
    return _redis_sse_service


async def get_sse_connection_manager(
    redis_sse_service: RedisSSEService = Depends(get_redis_sse_service),
) -> SSEConnectionManager:
    """Get SSE connection manager with dependency injection."""
    global _sse_connection_manager
    if _sse_connection_manager is None:
        async with _sse_connection_manager_lock:
            # Double-check pattern to prevent race conditions
            if _sse_connection_manager is None:
                _sse_connection_manager = SSEConnectionManager(redis_sse_service)
    return _sse_connection_manager


@router.get("/stream")
async def sse_stream(
    request: Request,
    sse_token: Annotated[str, Query(description="SSE authentication token")],
    sse_connection_manager: SSEConnectionManager = Depends(get_sse_connection_manager),
):
    """
    SSE streaming endpoint for real-time events.

    Establishes a Server-Sent Events connection for real-time event streaming.
    Supports Last-Event-ID header for reconnection and event history replay.

    Args:
        request: FastAPI request object for client disconnection detection
        sse_token: Short-term authentication token for SSE connection
        sse_connection_manager: SSE connection manager service

    Returns:
        EventSourceResponse: Server-Sent Events response stream

    Raises:
        HTTPException: 401 if authentication fails, 429 if connection limit exceeded
    """
    # Verify the token and get user ID
    user_id = await verify_sse_token(sse_token)

    try:
        # Use the existing SSE connection manager
        return await sse_connection_manager.add_connection(request, user_id)

    except HTTPException:
        # Re-raise HTTP exceptions (like 429 for rate limiting)
        raise
    except Exception as e:
        logger.error(f"Error establishing SSE connection for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to establish SSE connection"
        ) from e


@router.get("/health", response_model=SSEHealthResponse)
async def sse_health(
    sse_connection_manager: SSEConnectionManager = Depends(get_sse_connection_manager),
    redis_sse_service: RedisSSEService = Depends(get_redis_sse_service),
):
    """
    SSE service health check endpoint.

    Returns connection statistics and service health information.
    No authentication required for monitoring purposes.

    Returns:
        dict: Health status and connection statistics
    """
    import asyncio
    
    try:
        # Get connection statistics with timeout protection
        try:
            connection_stats = await asyncio.wait_for(
                sse_connection_manager.get_connection_count(),
                timeout=HEALTH_CHECK_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning("Connection statistics query timed out")
            # Provide safe defaults if stats query times out
            connection_stats = {
                "active_connections": -1,  # -1 indicates unavailable
                "redis_connection_counters": -1
            }
        except Exception as e:
            logger.warning(f"Failed to get connection statistics: {e}")
            connection_stats = {
                "active_connections": -1,
                "redis_connection_counters": -1
            }

        # Check Redis connectivity with timeout and proper encapsulation handling
        redis_healthy = False
        try:
            # Check if Redis service has a client initialized
            if hasattr(redis_sse_service, '_pubsub_client') and redis_sse_service._pubsub_client:
                # Use timeout for Redis ping operation
                await asyncio.wait_for(
                    redis_sse_service._pubsub_client.ping(),
                    timeout=HEALTH_CHECK_TIMEOUT
                )
                redis_healthy = True
            else:
                logger.warning("Redis client not initialized")
                redis_healthy = False
        except asyncio.TimeoutError:
            logger.warning("Redis health check timed out")
            redis_healthy = False
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_healthy = False

        # Determine overall service status
        overall_status = "healthy" if redis_healthy else "degraded"
        if connection_stats.get("active_connections", -1) == -1:
            overall_status = "unhealthy"  # Can't get basic stats

        health_data = SSEHealthResponse(
            status=overall_status,
            redis_status="healthy" if redis_healthy else "unhealthy",
            connection_statistics=ConnectionStatistics(**connection_stats),
            service="sse",
            version=SSE_SERVICE_VERSION,
        )

        # Return 503 if service is unhealthy or degraded
        if overall_status in ["unhealthy", "degraded"]:
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health_data.model_dump())

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = SSEHealthErrorResponse(
            status="unhealthy",
            error=str(e),
            service="sse",
            version=SSE_SERVICE_VERSION
        )
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=error_response.model_dump())
