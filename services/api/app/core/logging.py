import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set-cookie",
        "api_key",
        "secret",
        "auth_secret",
        "x-csrf-token",
    }
)
REDACTED = "[REDACTED]"
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _redact_value(key: str, value: Any) -> Any:
    if key.lower() in SENSITIVE_KEYS:
        return REDACTED
    if isinstance(value, Mapping):
        return {k: _redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, str):
        return _EMAIL_RE.sub("[EMAIL]", value)
    return value


def redact_sensitive(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor: never let secrets or emails reach log output."""
    for key in list(event_dict.keys()):
        event_dict[key] = _redact_value(key, event_dict[key])
    return event_dict


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_sensitive,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    # Route stdlib logging (uvicorn, sqlalchemy) through the same level; uvicorn's own access
    # log is disabled in favour of our middleware's structured access log.
    logging.basicConfig(level=level, stream=sys.stdout, format="%(message)s")
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
