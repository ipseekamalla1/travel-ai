"""arq worker configuration: `arq app.workers.settings.WorkerSettings`.

Jobs are registered here as phases add them (AI planning in Phase 9). The heartbeat job lets
operators confirm the worker is consuming the queue.
"""

from datetime import UTC, datetime
from typing import Any, ClassVar

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

WORKER_HEARTBEAT_KEY = "atu:worker:heartbeat"

log = get_logger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> str:
    now = datetime.now(UTC).isoformat()
    await ctx["redis"].set(WORKER_HEARTBEAT_KEY, now, ex=180)
    return now


async def startup(_ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.log_json)
    log.info("worker_startup", app_env=settings.app_env)


async def shutdown(_ctx: dict[str, Any]) -> None:
    log.info("worker_shutdown")


class WorkerSettings:
    functions: ClassVar[list[Any]] = [heartbeat]
    cron_jobs: ClassVar[list[Any]] = [cron(heartbeat, second=0)]  # once a minute
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))
