from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from app.auth.passwords import validate_password_strength

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128


def _normalize_email(value: str) -> str:
    return value.strip().lower()


Email = Annotated[EmailStr, AfterValidator(_normalize_email), Field(max_length=254)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
NewPassword = Annotated[
    str,
    Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH),
    AfterValidator(validate_password_strength),
]


class RegisterRequest(BaseModel):
    email: Email
    password: NewPassword
    display_name: DisplayName


class LoginRequest(BaseModel):
    email: Email
    # Login only bounds length: rules may change, and old passwords must still be checkable.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class CsrfTokenOut(BaseModel):
    csrf_token: str
