"""API v1 routes."""

from fastapi import APIRouter

from . import auth, events, novels

router = APIRouter()

# Include authentication routes
router.include_router(auth.router, prefix="/auth")

# Include events (SSE) routes
router.include_router(events.router, prefix="/events", tags=["sse"])

# Include novels routes
router.include_router(novels.router, prefix="/novels", tags=["novels"])

# Future routes will be added here
