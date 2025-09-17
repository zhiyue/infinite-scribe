"""Genesis API routes."""

from fastapi import APIRouter

from .flows import router as flows_router
from .stages import router as stages_router
from .stage_sessions import router as stage_sessions_router

router = APIRouter(prefix="/genesis", tags=["genesis"])

router.include_router(flows_router)
router.include_router(stages_router)
router.include_router(stage_sessions_router)

__all__ = ["router"]