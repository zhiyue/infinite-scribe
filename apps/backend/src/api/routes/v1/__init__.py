"""API v1 routes."""

from fastapi import APIRouter

from . import auth

router = APIRouter()

# Include authentication routes
router.include_router(auth.router, prefix="/auth")

# Future routes will be added here
