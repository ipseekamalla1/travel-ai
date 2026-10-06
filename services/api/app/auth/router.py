from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth.cookies import (
    CSRF_COOKIE,
    clear_session_cookie,
    set_csrf_cookie,
    set_session_cookie,
)
from app.auth.dependencies import (
    AuthServiceDep,
    ClientIp,
    CurrentAuthDep,
    CurrentUser,
    OptionalAuth,
    RateLimiterDep,
    SettingsDep,
    get_client_info,
)
from app.auth.schemas import CsrfTokenOut, LoginRequest, RegisterRequest
from app.auth.service import ClientInfo
from app.core.config import Settings
from app.core.security import csrf_token_is_valid, new_csrf_token
from app.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

RATE_WINDOW_S = 60
ClientInfoDep = Annotated[ClientInfo, Depends(get_client_info)]


def _issue_cookies(response: Response, token: str, settings: Settings) -> None:
    set_session_cookie(response, token, settings)
    # Rotate the CSRF token whenever the session changes.
    set_csrf_cookie(response, new_csrf_token(settings.auth_secret.get_secret_value()), settings)


@router.get("/csrf", response_model=CsrfTokenOut, summary="Get (or create) the CSRF token")
async def csrf_token(request: Request, response: Response, settings: SettingsDep) -> CsrfTokenOut:
    secret = settings.auth_secret.get_secret_value()
    existing = request.cookies.get(CSRF_COOKIE)
    if existing and csrf_token_is_valid(existing, existing, secret):
        token = existing
    else:
        token = new_csrf_token(secret)
    set_csrf_cookie(response, token, settings)
    return CsrfTokenOut(csrf_token=token)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and sign in",
)
async def register(
    data: RegisterRequest,
    response: Response,
    service: AuthServiceDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
    ip: ClientIp,
    client: ClientInfoDep,
) -> UserOut:
    await limiter.hit(
        "register:ip", ip, limit=settings.rate_limit_auth_per_minute, window_s=RATE_WINDOW_S
    )
    issued = await service.register(data, client)
    _issue_cookies(response, issued.token, settings)
    return UserOut.model_validate(issued.user)


@router.post("/login", response_model=UserOut, summary="Sign in with email and password")
async def login(
    data: LoginRequest,
    response: Response,
    service: AuthServiceDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
    ip: ClientIp,
    client: ClientInfoDep,
) -> UserOut:
    limit = settings.rate_limit_auth_per_minute
    await limiter.hit("login:ip", ip, limit=limit, window_s=RATE_WINDOW_S)
    await limiter.hit("login:email", data.email, limit=max(limit // 2, 1), window_s=RATE_WINDOW_S)
    issued = await service.login(data, client)
    _issue_cookies(response, issued.token, settings)
    return UserOut.model_validate(issued.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out of this session")
async def logout(
    response: Response, auth: OptionalAuth, service: AuthServiceDep, settings: SettingsDep
) -> None:
    # Idempotent: clears the cookie even when the session is already gone.
    if auth is not None:
        await service.logout(auth.session)
    clear_session_cookie(response, settings)


@router.post(
    "/logout-all", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out of every session"
)
async def logout_all(
    response: Response, auth: CurrentAuthDep, service: AuthServiceDep, settings: SettingsDep
) -> None:
    await service.logout_all(auth.user)
    clear_session_cookie(response, settings)


@router.get("/me", response_model=UserOut, summary="The signed-in user")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
