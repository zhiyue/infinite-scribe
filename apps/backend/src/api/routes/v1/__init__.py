"""API v1 routes."""

from fastapi import APIRouter

from . import auth, events

router = APIRouter()

# Include authentication routes
router.include_router(auth.router, prefix="/auth")

# Include events (SSE) routes
router.include_router(events.router, prefix="/events")

# Future routes will be added here
