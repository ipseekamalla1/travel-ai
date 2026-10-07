from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.money import SUPPORTED_CURRENCIES
from app.travel_profiles import registry
from app.travel_profiles.models import TravelProfile
from app.travel_profiles.repository import TravelProfileRepository
from app.travel_profiles.schemas import (
    OptionOut,
    PreferenceGroupOut,
    PreferenceKeyOut,
    PreferenceOut,
    PreferencesPatch,
    TravelProfileOptions,
    TravelProfileOut,
    TravelProfileUpdate,
)
from app.users.models import User


class TravelProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._profiles = TravelProfileRepository(db)

    async def _to_out(self, profile: TravelProfile) -> TravelProfileOut:
        preferences = await self._profiles.list_preferences(profile.user_id)
        # Validating (not constructing) re-checks DB values against the current registry enums.
        return TravelProfileOut.model_validate(
            {
                "travel_styles": profile.travel_styles,
                "pace": profile.pace,
                "budget_style": profile.budget_style,
                "accommodation_style": profile.accommodation_style,
                "walking_tolerance": profile.walking_tolerance,
                "dietary": profile.dietary,
                "day_start": profile.day_start,
                "day_end": profile.day_end,
                "onboarding_completed": profile.onboarding_completed_at is not None,
                "preferences": [PreferenceOut.model_validate(p) for p in preferences],
            }
        )

    async def get(self, user: User) -> TravelProfileOut:
        profile = await self._profiles.get_or_create(user.id)
        await self._db.commit()
        return await self._to_out(profile)

    async def replace(self, user: User, data: TravelProfileUpdate) -> TravelProfileOut:
        profile = await self._profiles.get_or_create(user.id)
        for field, value in data.model_dump().items():
            setattr(profile, field, value)
        await self._db.commit()
        return await self._to_out(profile)

    async def patch_preferences(self, user: User, patch: PreferencesPatch) -> TravelProfileOut:
        profile = await self._profiles.get_or_create(user.id)
        await self._profiles.upsert_preferences(
            user.id, {item.key: item.weight for item in patch.upsert}, source=patch.source
        )
        await self._profiles.remove_preferences(user.id, patch.remove)
        await self._db.commit()
        return await self._to_out(profile)

    async def complete_onboarding(self, user: User) -> TravelProfileOut:
        profile = await self._profiles.get_or_create(user.id)
        if profile.onboarding_completed_at is None:
            profile.onboarding_completed_at = datetime.now(UTC)
        await self._db.commit()
        return await self._to_out(profile)


def _options(items: tuple[registry.Option, ...]) -> list[OptionOut]:
    return [OptionOut(value=o.value, label=o.label, description=o.description) for o in items]


def travel_profile_options() -> TravelProfileOptions:
    groups = [
        PreferenceGroupOut(
            id=group.value,
            label=group.label,
            keys=[
                PreferenceKeyOut(key=k.key, label=k.label, description=k.description)
                for k in registry.PREFERENCE_KEYS
                if k.group == group.value
            ],
        )
        for group in registry.PREFERENCE_GROUPS
    ]
    return TravelProfileOptions(
        travel_styles=_options(registry.TRAVEL_STYLES),
        max_travel_styles=registry.MAX_TRAVEL_STYLES,
        paces=_options(registry.PACES),
        budget_styles=_options(registry.BUDGET_STYLES),
        accommodation_styles=_options(registry.ACCOMMODATION_STYLES),
        walking_tolerances=_options(registry.WALKING_TOLERANCES),
        dietary=_options(registry.DIETARY),
        preference_groups=groups,
        currencies=list(SUPPORTED_CURRENCIES),
    )
