import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.common.money import SUPPORTED_CURRENCY_SET


def _supported_currency(code: str) -> str:
    code = code.upper()
    if code not in SUPPORTED_CURRENCY_SET:
        raise ValueError(f"{code} isn't a supported currency.")
    return code


Currency = Annotated[str, AfterValidator(_supported_currency)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    home_currency: str
    locale: str
    units: str
    onboarding_completed: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """PATCH /me — only the fields sent are changed."""

    display_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] | None
    ) = None
    home_currency: Currency | None = None
    units: Literal["metric", "imperial"] | None = None
