import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.travel_profiles.models import TravelPreference, TravelProfile


class TravelProfileRepository:
    """All queries are scoped by `user_id`: there is no way to read another user's profile."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get(self, user_id: uuid.UUID) -> TravelProfile | None:
        return await self._db.scalar(select(TravelProfile).where(TravelProfile.user_id == user_id))

    async def get_or_create(self, user_id: uuid.UUID) -> TravelProfile:
        # Insert-if-missing is race-safe; the unique user_id constraint makes it idempotent.
        await self._db.execute(
            insert(TravelProfile)
            .values(id=uuid.uuid7(), user_id=user_id)
            .on_conflict_do_nothing(index_elements=[TravelProfile.user_id])
        )
        profile = await self.get(user_id)
        assert profile is not None
        return profile

    async def onboarding_completed(self, user_id: uuid.UUID) -> bool:
        completed_at = await self._db.scalar(
            select(TravelProfile.onboarding_completed_at).where(TravelProfile.user_id == user_id)
        )
        return completed_at is not None

    async def list_preferences(self, user_id: uuid.UUID) -> list[TravelPreference]:
        result = await self._db.scalars(
            select(TravelPreference)
            .where(TravelPreference.user_id == user_id)
            .order_by(TravelPreference.key)
        )
        return list(result)

    async def upsert_preferences(
        self, user_id: uuid.UUID, weights: dict[str, object], *, source: str
    ) -> None:
        if not weights:
            return
        statement = insert(TravelPreference).values(
            [
                {
                    "id": uuid.uuid7(),
                    "user_id": user_id,
                    "key": key,
                    "weight": weight,
                    "source": source,
                }
                for key, weight in weights.items()
            ]
        )
        await self._db.execute(
            statement.on_conflict_do_update(
                index_elements=[TravelPreference.user_id, TravelPreference.key],
                set_={
                    "weight": statement.excluded.weight,
                    "source": statement.excluded.source,
                    "confidence": 1,
                    "updated_at": func.now(),
                },
            )
        )

    async def remove_preferences(self, user_id: uuid.UUID, keys: list[str]) -> None:
        if not keys:
            return
        await self._db.execute(
            delete(TravelPreference).where(
                TravelPreference.user_id == user_id, TravelPreference.key.in_(keys)
            )
        )
