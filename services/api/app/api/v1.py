from fastapi import APIRouter

from app.health.router import router as health_router

API_V1_PREFIX = "/api/v1"

router = APIRouter(prefix=API_V1_PREFIX)
router.include_router(health_router)
