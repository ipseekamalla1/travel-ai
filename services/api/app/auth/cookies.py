from datetime import timedelta

from fastapi import Response

from app.core.config import Settings

SESSION_COOKIE = "atu_session"
CSRF_COOKIE = "atu_csrf"
CSRF_HEADER = "X-CSRF-Token"


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(timedelta(days=settings.session_absolute_days).total_seconds()),
        httponly=True,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, secure=settings.cookies_secure, samesite="lax", path="/"
    )


def set_csrf_cookie(response: Response, token: str, settings: Settings) -> None:
    # Readable by JavaScript on purpose: the client echoes it in the X-CSRF-Token header.
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=int(timedelta(days=settings.session_absolute_days).total_seconds()),
        httponly=False,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
    )
