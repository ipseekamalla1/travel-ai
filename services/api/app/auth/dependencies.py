from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.auth.models import Session
from app.auth.service import AuthService, ClientInfo
from app.core.config import Settings
from app.core.db import get_session
from app.core.errors import AppError, UnauthenticatedError
from app.core.rate_limit import RateLimiter, client_ip, ip_prefix
from app.core.security import csrf_token_is_valid
from app.users.models import User

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CsrfFailedError(AppError):
    status, code, title = 403, "CSRF_FAILED", "Request could not be verified"


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSession = Annotated[AsyncSession, Depends(get_session)]


def get_auth_service(db: DbSession, settings: SettingsDep) -> AuthService:
    return AuthService(db, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_rate_limiter(request: Request) -> RateLimiter:
    return RateLimiter(request.app.state.redis)


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def get_client_ip(request: Request, settings: SettingsDep) -> str:
    return client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)


ClientIp = Annotated[str, Depends(get_client_ip)]


def get_client_info(request: Request, ip: ClientIp) -> ClientInfo:
    return ClientInfo(ip_prefix=ip_prefix(ip), user_agent=request.headers.get("user-agent"))


@dataclass(frozen=True)
class CurrentAuth:
    user: User
    session: Session


async def get_optional_auth(request: Request, service: AuthServiceDep) -> CurrentAuth | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    resolved = await service.resolve(token)
    return CurrentAuth(user=resolved[0], session=resolved[1]) if resolved else None


OptionalAuth = Annotated[CurrentAuth | None, Depends(get_optional_auth)]


async def get_current_auth(auth: OptionalAuth) -> CurrentAuth:
    if auth is None:
        raise UnauthenticatedError("Please sign in to continue.")
    return auth


async def get_current_user(auth: Annotated[CurrentAuth, Depends(get_current_auth)]) -> User:
    return auth.user


CurrentAuthDep = Annotated[CurrentAuth, Depends(get_current_auth)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_csrf(request: Request, settings: SettingsDep) -> None:
    """Applied to every API route; enforces CSRF only on state-changing methods.

    Two layers: the Origin header (when sent) must be an allowed origin, and the signed
    double-submit token in the header must match the cookie.
    """
    if request.method not in UNSAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is not None:
        own_origin = str(request.base_url).rstrip("/")
        if origin.rstrip("/") not in settings.allowed_origins | {own_origin}:
            raise CsrfFailedError("This request came from an untrusted origin.")
    if not csrf_token_is_valid(
        request.cookies.get(CSRF_COOKIE),
        request.headers.get(CSRF_HEADER),
        settings.auth_secret.get_secret_value(),
    ):
        raise CsrfFailedError("Missing or invalid CSRF token. Refresh the page and try again.")
