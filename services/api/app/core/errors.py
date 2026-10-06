"""Application errors and the RFC 9457-style error envelope (see docs/API.md §1.1)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.request_context import get_request_id

PROBLEM_JSON = "application/problem+json"
ERROR_TYPE_BASE = "https://errors.atu.dev/"

log = get_logger(__name__)


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class Problem(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str | None = None
    errors: list[FieldError] = []
    request_id: str | None = None


class AppError(Exception):
    """Base for errors raised by services. Never carries internal details to the client."""

    status: int = 500
    code: str = "INTERNAL_ERROR"
    title: str = "Internal server error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        errors: list[FieldError] | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.errors = errors or []
        if code:
            self.code = code


class BadRequestError(AppError):
    status, code, title = 400, "BAD_REQUEST", "Bad request"


class UnauthenticatedError(AppError):
    status, code, title = 401, "UNAUTHENTICATED", "Authentication required"


class ForbiddenError(AppError):
    status, code, title = 403, "FORBIDDEN", "Forbidden"


class NotFoundError(AppError):
    status, code, title = 404, "NOT_FOUND", "Not found"


class ConflictError(AppError):
    status, code, title = 409, "CONFLICT", "Conflict"


class ValidationFailedError(AppError):
    status, code, title = 422, "VALIDATION_ERROR", "Validation failed"


class RateLimitedError(AppError):
    status, code, title = 429, "RATE_LIMITED", "Too many requests"


class ProviderUnavailableError(AppError):
    status, code, title = 503, "PROVIDER_UNAVAILABLE", "A required service is unavailable"


_HTTP_CODES: dict[int, tuple[str, str]] = {
    400: ("BAD_REQUEST", "Bad request"),
    401: ("UNAUTHENTICATED", "Authentication required"),
    403: ("FORBIDDEN", "Forbidden"),
    404: ("NOT_FOUND", "Not found"),
    405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
    409: ("CONFLICT", "Conflict"),
    413: ("PAYLOAD_TOO_LARGE", "Payload too large"),
    415: ("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
    429: ("RATE_LIMITED", "Too many requests"),
}


def _slug(code: str) -> str:
    return code.lower().replace("_", "-")


def problem_response(
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    errors: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = Problem(
        type=ERROR_TYPE_BASE + _slug(code),
        title=title,
        status=status,
        code=code,
        detail=detail,
        errors=errors or [],
        request_id=get_request_id(),
    )
    return JSONResponse(
        body.model_dump(), status_code=status, media_type=PROBLEM_JSON, headers=headers
    )


def _field_path(loc: tuple[Any, ...]) -> str:
    # Drop the "body"/"query"/"path" prefix FastAPI adds; keep nested paths dotted.
    parts = [str(p) for p in loc[1:]] if loc and loc[0] in {"body", "query", "path"} else list(loc)
    return ".".join(str(p) for p in parts) or "body"


async def _app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    if exc.status >= 500:
        log.error("app_error", code=exc.code, error=str(exc))
    return problem_response(
        status=exc.status, code=exc.code, title=exc.title, detail=exc.detail, errors=exc.errors
    )


async def _validation_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        FieldError(
            field=_field_path(tuple(err["loc"])), code=err["type"].upper(), message=err["msg"]
        )
        for err in exc.errors()
    ]
    return problem_response(
        status=422,
        code="VALIDATION_ERROR",
        title="Validation failed",
        detail="One or more fields are invalid.",
        errors=errors,
    )


async def _http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, title = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", "Request failed"))
    return problem_response(
        status=exc.status_code, code=code, title=title, headers=getattr(exc, "headers", None)
    )


async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", error_type=type(exc).__name__)
    return problem_response(status=500, code="INTERNAL_ERROR", title="Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
