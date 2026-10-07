from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUser, DbSession
from app.travel_profiles.schemas import (
    PreferencesPatch,
    TravelProfileOptions,
    TravelProfileOut,
    TravelProfileUpdate,
)
from app.travel_profiles.service import TravelProfileService, travel_profile_options

router = APIRouter(tags=["travel-profile"])


def get_service(db: DbSession) -> TravelProfileService:
    return TravelProfileService(db)


ServiceDep = Annotated[TravelProfileService, Depends(get_service)]


@router.get(
    "/meta/travel-profile-options",
    response_model=TravelProfileOptions,
    summary="Allowed travel-profile values and labels",
)
async def options() -> TravelProfileOptions:
    return travel_profile_options()


@router.get("/me/travel-profile", response_model=TravelProfileOut, summary="Your travel profile")
async def get_profile(user: CurrentUser, service: ServiceDep) -> TravelProfileOut:
    return await service.get(user)


@router.put(
    "/me/travel-profile", response_model=TravelProfileOut, summary="Replace core profile fields"
)
async def replace_profile(
    data: TravelProfileUpdate, user: CurrentUser, service: ServiceDep
) -> TravelProfileOut:
    return await service.replace(user, data)


@router.patch(
    "/me/travel-profile/preferences",
    response_model=TravelProfileOut,
    summary="Add, change or remove weighted preferences",
)
async def patch_preferences(
    patch: PreferencesPatch, user: CurrentUser, service: ServiceDep
) -> TravelProfileOut:
    return await service.patch_preferences(user, patch)


@router.post(
    "/me/travel-profile/complete-onboarding",
    response_model=TravelProfileOut,
    summary="Mark onboarding as finished",
)
async def complete_onboarding(user: CurrentUser, service: ServiceDep) -> TravelProfileOut:
    return await service.complete_onboarding(user)
