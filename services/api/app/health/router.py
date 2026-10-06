import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.logging import get_logger
from app.core.redis import get_redis

router = APIRouter(prefix="/health", tags=["health"])
log = get_logger(__name__)

ComponentStatus = Literal["ok", "unavailable"]


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    components: dict[str, ComponentStatus]


@router.get("", response_model=LivenessResponse, summary="Liveness probe")
async def liveness() -> LivenessResponse:
    return LivenessResponse()


async def _check_database(session: AsyncSession) -> None:
    await session.execute(text("SELECT 1"))


async def _check_redis(redis: Redis) -> None:
    await redis.ping()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
    summary="Readiness probe (database + redis)",
)
async def readiness(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> JSONResponse:
    timeout = request.app.state.settings.readiness_timeout_s
    checks = {"database": _check_database(session), "redis": _check_redis(redis)}
    components: dict[str, ComponentStatus] = {}
    for name, check in checks.items():
        try:
            await asyncio.wait_for(check, timeout=timeout)
            components[name] = "ok"
        except Exception as exc:  # any failure means "not ready"; details go to logs only
            log.warning("readiness_check_failed", component=name, error_type=type(exc).__name__)
            components[name] = "unavailable"

    ready = all(status == "ok" for status in components.values())
    body = ReadinessResponse(status="ok" if ready else "unavailable", components=components)
    return JSONResponse(body.model_dump(), status_code=200 if ready else 503)
