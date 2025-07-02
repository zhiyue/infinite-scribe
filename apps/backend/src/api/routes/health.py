"""Health check endpoints."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.common.services.embedding_service import embedding_service
from src.common.services.neo4j_service import neo4j_service
from src.common.services.postgres_service import postgres_service
from src.common.services.redis_service import redis_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint with all service connectivity verification."""
    try:
        timestamp = datetime.now(UTC).isoformat()

        # 检查所有核心服务
        postgres_healthy = await postgres_service.check_connection()
        neo4j_healthy = await neo4j_service.check_connection()
        redis_healthy = await redis_service.check_connection()
        embedding_healthy = await embedding_service.check_connection()

        # 构建服务状态详情
        services = {
            "database": "healthy" if postgres_healthy else "unhealthy",
            "neo4j": "healthy" if neo4j_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "embedding": "healthy" if embedding_healthy else "unhealthy",
        }

        # 记录失败的服务
        failed_services = [name for name, status in services.items() if status == "unhealthy"]
        if failed_services:
            logger.warning(f"Service health check failed: {', '.join(failed_services)}")

        # 确定整体状态 - 核心服务(postgres, neo4j)必须健康, 其他服务可选
        core_services_healthy = postgres_healthy and neo4j_healthy
        overall_healthy = core_services_healthy  # 可根据需要调整策略

        if overall_healthy:
            return {"status": "healthy", "timestamp": timestamp, "services": services}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": timestamp,
                    "services": services,
                    "failed": failed_services,
                },
            )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint with schema verification."""
    try:
        # Check basic connectivity
        postgres_connected = await postgres_service.check_connection()
        neo4j_connected = await neo4j_service.check_connection()

        if not (postgres_connected and neo4j_connected):
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "reason": "Database connections not established"},
            )

        # Verify schema
        postgres_schema_ok = await postgres_service.verify_schema()
        neo4j_constraints_ok = await neo4j_service.verify_constraints()

        if postgres_schema_ok and neo4j_constraints_ok:
            return {"status": "ready", "service": "api-gateway"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not ready",
                    "postgres_schema": postgres_schema_ok,
                    "neo4j_constraints": neo4j_constraints_ok,
                },
            )
    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})
