from sqlalchemy.ext.asyncio import AsyncSession

from app.travel_profiles.repository import TravelProfileRepository
from app.users.models import User
from app.users.schemas import UserOut, UserUpdate


async def user_out(db: AsyncSession, user: User) -> UserOut:
    completed = await TravelProfileRepository(db).onboarding_completed(user.id)
    return UserOut.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "home_currency": user.home_currency,
            "locale": user.locale,
            "units": user.units,
            "onboarding_completed": completed,
            "created_at": user.created_at,
        }
    )


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> UserOut:
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    return await user_out(db, user)
