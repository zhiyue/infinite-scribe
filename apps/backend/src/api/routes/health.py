"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "api-gateway"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Add actual readiness checks (DB connections, etc.)
    return {"status": "ready", "service": "api-gateway"}