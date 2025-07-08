"""Authentication API routes."""

from fastapi import APIRouter

from . import auth_login, auth_password, auth_profile, auth_register

router = APIRouter()

# Include all authentication-related routes
router.include_router(auth_register.router, tags=["auth"])
router.include_router(auth_login.router, tags=["auth"])
router.include_router(auth_password.router, tags=["auth"])
router.include_router(auth_profile.router, tags=["auth"])
