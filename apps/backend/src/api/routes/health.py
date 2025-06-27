"""Health check endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.common.services.neo4j_service import neo4j_service
from src.common.services.postgres_service import postgres_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Health check endpoint with database connectivity verification."""
    try:
        # Check PostgreSQL connection
        postgres_healthy = await postgres_service.check_connection()

        # Check Neo4j connection
        neo4j_healthy = await neo4j_service.check_connection()

        # Return ok only if both databases are connected
        if postgres_healthy and neo4j_healthy:
            return {"status": "ok"}
        else:
            # Log specific failures
            if not postgres_healthy:
                logger.warning("PostgreSQL health check failed")
            if not neo4j_healthy:
                logger.warning("Neo4j health check failed")

            # Return 503 Service Unavailable
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "postgres": postgres_healthy,
                    "neo4j": neo4j_healthy,
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
