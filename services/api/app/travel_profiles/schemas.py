from collections.abc import Callable
from datetime import datetime, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.travel_profiles.registry import (
    DIETARY_VALUES,
    MAX_TRAVEL_STYLES,
    PREFERENCE_KEYS_BY_KEY,
    TRAVEL_STYLE_VALUES,
    AccommodationStyle,
    BudgetStyle,
    Pace,
    WalkingTolerance,
)


def _unique_known(allowed: frozenset[str], what: str) -> Callable[[list[str]], list[str]]:
    def validate(values: list[str]) -> list[str]:
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise ValueError(f"Unknown {what}: {', '.join(unknown)}.")
        if len(set(values)) != len(values):
            raise ValueError(f"Each {what} may only appear once.")
        return values

    return validate


def _known_preference_key(key: str) -> str:
    if key not in PREFERENCE_KEYS_BY_KEY:
        raise ValueError(f"Unknown preference key: {key}.")
    return key


TravelStyles = Annotated[
    list[str],
    Field(max_length=MAX_TRAVEL_STYLES),
    AfterValidator(_unique_known(TRAVEL_STYLE_VALUES, "travel style")),
]
Dietary = Annotated[list[str], AfterValidator(_unique_known(DIETARY_VALUES, "dietary need"))]
PreferenceKeyName = Annotated[str, AfterValidator(_known_preference_key)]
Weight = Annotated[Decimal, Field(ge=-1, le=1, max_digits=4, decimal_places=3)]


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    weight: float
    source: str
    updated_at: datetime


class TravelProfileFields(BaseModel):
    travel_styles: TravelStyles = []
    pace: Pace = Pace.BALANCED
    budget_style: BudgetStyle = BudgetStyle.MODERATE
    accommodation_style: AccommodationStyle | None = None
    walking_tolerance: WalkingTolerance = WalkingTolerance.MEDIUM
    dietary: Dietary = []
    day_start: time = time(9, 0)
    day_end: time = time(21, 0)

    @model_validator(mode="after")
    def _day_window(self) -> TravelProfileFields:
        if self.day_end <= self.day_start:
            raise ValueError("day_end must be later than day_start.")
        return self


class TravelProfileUpdate(TravelProfileFields):
    """Full replacement of the core profile fields (PUT)."""


class TravelProfileOut(TravelProfileFields):
    model_config = ConfigDict(from_attributes=True)

    onboarding_completed: bool
    preferences: list[PreferenceOut]


class PreferenceUpsert(BaseModel):
    key: PreferenceKeyName
    weight: Weight


class PreferencesPatch(BaseModel):
    upsert: list[PreferenceUpsert] = Field(default=[], max_length=100)
    remove: list[PreferenceKeyName] = Field(default=[], max_length=100)
    source: Literal["onboarding", "explicit"] = "explicit"

    @model_validator(mode="after")
    def _no_conflicts(self) -> PreferencesPatch:
        upsert_keys = [item.key for item in self.upsert]
        if len(set(upsert_keys)) != len(upsert_keys):
            raise ValueError("A preference key may only be upserted once per request.")
        if set(upsert_keys) & set(self.remove):
            raise ValueError("A preference key can't be both upserted and removed.")
        return self


# ---------- options (GET /meta/travel-profile-options) ----------


class OptionOut(BaseModel):
    value: str
    label: str
    description: str


class PreferenceKeyOut(BaseModel):
    key: str
    label: str
    description: str


class PreferenceGroupOut(BaseModel):
    id: str
    label: str
    keys: list[PreferenceKeyOut]


class TravelProfileOptions(BaseModel):
    travel_styles: list[OptionOut]
    max_travel_styles: int
    paces: list[OptionOut]
    budget_styles: list[OptionOut]
    accommodation_styles: list[OptionOut]
    walking_tolerances: list[OptionOut]
    dietary: list[OptionOut]
    preference_groups: list[PreferenceGroupOut]
    currencies: list[str]
