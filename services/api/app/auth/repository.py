import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Session


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    def add(self, auth_session: Session) -> None:
        self._db.add(auth_session)

    async def get_by_token_hash(self, token_hash: bytes) -> Session | None:
        return await self._db.scalar(select(Session).where(Session.token_hash == token_hash))

    async def revoke_all_for_user(self, user_id: uuid.UUID, *, now: datetime) -> None:
        await self._db.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def delete_stale(self, *, now: datetime, revoked_grace: timedelta) -> int:
        """Remove expired sessions and revoked ones older than the grace period."""
        result = await self._db.execute(
            delete(Session).where(
                or_(
                    Session.expires_at < now,
                    Session.absolute_expires_at < now,
                    Session.revoked_at < now - revoked_grace,
                )
            )
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
