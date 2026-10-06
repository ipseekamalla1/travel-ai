"""arq worker configuration: `arq app.workers.settings.WorkerSettings`.

Jobs are registered here as phases add them (AI planning in Phase 9). The heartbeat job lets
operators confirm the worker is consuming the queue.
"""

from datetime import UTC, datetime
from typing import Any, ClassVar

from arq.connections import RedisSettings
from arq.cron import cron

from app.auth.service import AuthService
from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.logging import configure_logging, get_logger

WORKER_HEARTBEAT_KEY = "atu:worker:heartbeat"

log = get_logger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> str:
    now = datetime.now(UTC).isoformat()
    await ctx["redis"].set(WORKER_HEARTBEAT_KEY, now, ex=180)
    return now


async def delete_stale_sessions(ctx: dict[str, Any]) -> int:
    async with ctx["session_factory"]() as db:
        removed = await AuthService(db, ctx["settings"]).delete_stale_sessions()
    log.info("stale_sessions_deleted", count=removed)
    return removed


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)
    engine = create_engine(settings)
    ctx.update(settings=settings, engine=engine, session_factory=create_session_factory(engine))
    log.info("worker_startup", app_env=settings.app_env)


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()
    log.info("worker_shutdown")


class WorkerSettings:
    functions: ClassVar[list[Any]] = [heartbeat, delete_stale_sessions]
    cron_jobs: ClassVar[list[Any]] = [
        cron(heartbeat, second=0),  # every minute
        cron(delete_stale_sessions, hour=3, minute=17, second=0),  # daily, off-peak
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))
