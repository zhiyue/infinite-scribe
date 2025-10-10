"""API v1 routes."""

from fastapi import APIRouter

from . import auth, conversations, events, novels
from .genesis import router as genesis_router

router = APIRouter()

# Include authentication routes
router.include_router(auth.router, prefix="/auth")

# Include events (SSE) routes
router.include_router(events.router, prefix="/events", tags=["sse"])

# Include novels routes
router.include_router(novels.router, prefix="/novels", tags=["novels"])

# Include Genesis routes
router.include_router(genesis_router, prefix="/genesis")

# Include conversations routes
router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
