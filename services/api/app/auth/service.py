"""Authentication: registration, login, session resolution and revocation (ADR-004)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Session
from app.auth.repository import SessionRepository
from app.auth.schemas import LoginRequest, RegisterRequest
from app.core.config import Settings
from app.core.errors import AppError, ConflictError, FieldError
from app.core.logging import get_logger
from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    password_needs_rehash,
    verify_password,
)
from app.users.models import User
from app.users.repository import UserRepository

log = get_logger(__name__)

# Sliding-expiry writes are throttled so every request doesn't update the session row.
SESSION_TOUCH_INTERVAL = timedelta(minutes=5)
REVOKED_SESSION_RETENTION = timedelta(days=7)


class InvalidCredentialsError(AppError):
    status, code, title = 401, "INVALID_CREDENTIALS", "Invalid email or password"


@dataclass(frozen=True)
class ClientInfo:
    ip_prefix: str | None
    user_agent: str | None


@dataclass(frozen=True)
class IssuedSession:
    user: User
    token: str  # raw token: goes into the cookie only, never stored or logged
    session: Session


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._users = UserRepository(db)
        self._sessions = SessionRepository(db)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def _new_session(self, user: User, client: ClientInfo) -> tuple[str, Session]:
        now = self._now()
        token = new_session_token()
        absolute = now + timedelta(days=self._settings.session_absolute_days)
        auth_session = Session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=min(now + timedelta(days=self._settings.session_idle_days), absolute),
            absolute_expires_at=absolute,
            last_seen_at=now,
            user_agent=(client.user_agent or "")[:256] or None,
            ip_prefix=client.ip_prefix,
        )
        self._sessions.add(auth_session)
        return token, auth_session

    async def register(self, data: RegisterRequest, client: ClientInfo) -> IssuedSession:
        email_taken = ConflictError(
            "An account with this email already exists.",
            code="EMAIL_TAKEN",
            errors=[
                FieldError(
                    field="email", code="EMAIL_TAKEN", message="This email is already registered."
                )
            ],
        )
        if await self._users.get_by_email(data.email) is not None:
            raise email_taken

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            last_login_at=self._now(),
        )
        self._users.add(user)
        try:
            await self._db.flush()  # assigns defaults; surfaces a concurrent duplicate email
        except IntegrityError as exc:
            await self._db.rollback()
            raise email_taken from exc

        token, auth_session = self._new_session(user, client)
        await self._db.commit()
        log.info("user_registered", user_id=str(user.id))
        return IssuedSession(user=user, token=token, session=auth_session)

    async def login(self, data: LoginRequest, client: ClientInfo) -> IssuedSession:
        user = await self._users.get_by_email(data.email)
        # Always runs one argon2 verify, so unknown emails take as long as wrong passwords.
        password_ok = verify_password(user.password_hash if user else None, data.password)
        if user is None or not password_ok or not user.is_active:
            log.info("login_failed", reason="invalid_credentials")
            raise InvalidCredentialsError("The email or password is incorrect.")

        if user.password_hash and password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password)
        user.last_login_at = self._now()
        token, auth_session = self._new_session(user, client)
        await self._db.commit()
        log.info("login_succeeded", user_id=str(user.id))
        return IssuedSession(user=user, token=token, session=auth_session)

    async def resolve(self, token: str) -> tuple[User, Session] | None:
        """Return the active user + session for a cookie token, extending idle expiry."""
        auth_session = await self._sessions.get_by_token_hash(hash_session_token(token))
        now = self._now()
        if (
            auth_session is None
            or auth_session.revoked_at is not None
            or auth_session.expires_at <= now
            or auth_session.absolute_expires_at <= now
        ):
            return None

        user = await self._users.get_by_id(auth_session.user_id)
        if user is None or not user.is_active:
            return None

        if now - auth_session.last_seen_at >= SESSION_TOUCH_INTERVAL:
            auth_session.last_seen_at = now
            auth_session.expires_at = min(
                now + timedelta(days=self._settings.session_idle_days),
                auth_session.absolute_expires_at,
            )
            await self._db.commit()
        return user, auth_session

    async def logout(self, auth_session: Session) -> None:
        auth_session.revoked_at = self._now()
        await self._db.commit()

    async def logout_all(self, user: User) -> None:
        await self._sessions.revoke_all_for_user(user.id, now=self._now())
        await self._db.commit()

    async def delete_stale_sessions(self) -> int:
        removed = await self._sessions.delete_stale(
            now=self._now(), revoked_grace=REVOKED_SESSION_RETENTION
        )
        await self._db.commit()
        return removed
