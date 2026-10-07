from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DbSession
from app.users.schemas import UserOut, UserUpdate
from app.users.service import update_user, user_out

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserOut, summary="Your account")
async def get_me(user: CurrentUser, db: DbSession) -> UserOut:
    return await user_out(db, user)


@router.patch("", response_model=UserOut, summary="Update account settings")
async def patch_me(data: UserUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    return await update_user(db, user, data)
