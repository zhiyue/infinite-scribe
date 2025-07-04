"""API v1 routes."""

from fastapi import APIRouter

from .genesis import router as genesis_router

router = APIRouter()

# Include Genesis routes
router.include_router(genesis_router)

# Future routes will be added here
