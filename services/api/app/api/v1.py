from fastapi import APIRouter, Depends

from app.auth.dependencies import require_csrf
from app.auth.router import router as auth_router
from app.health.router import router as health_router

API_V1_PREFIX = "/api/v1"

# CSRF protection applies to every state-changing route (it is a no-op for safe methods).
router = APIRouter(prefix=API_V1_PREFIX, dependencies=[Depends(require_csrf)])
router.include_router(health_router)
router.include_router(auth_router)
