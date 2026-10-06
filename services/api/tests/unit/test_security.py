import pytest

from app.auth.passwords import validate_password_strength
from app.core.rate_limit import ip_prefix
from app.core.security import (
    csrf_token_is_valid,
    hash_password,
    new_csrf_token,
    verify_password,
)

SECRET = "s" * 48


def test_password_hash_round_trip() -> None:
    hashed = hash_password("a-long-passphrase")

    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "a-long-passphrase")
    assert not verify_password(hashed, "a-long-passphrasE")


def test_verify_without_hash_is_false() -> None:
    assert not verify_password(None, "anything-at-all")


def test_verify_with_corrupt_hash_is_false() -> None:
    assert not verify_password("not-a-hash", "anything-at-all")


def test_csrf_token_validates_against_matching_cookie() -> None:
    token = new_csrf_token(SECRET)

    assert csrf_token_is_valid(token, token, SECRET)


@pytest.mark.parametrize(
    ("cookie", "header"),
    [(None, "x"), ("x", None), ("a.b", "a.c")],
)
def test_csrf_token_rejects_missing_or_mismatched(cookie: str | None, header: str | None) -> None:
    assert not csrf_token_is_valid(cookie, header, SECRET)


def test_csrf_token_signed_with_other_secret_is_rejected() -> None:
    token = new_csrf_token("other-secret")

    assert not csrf_token_is_valid(token, token, SECRET)


@pytest.mark.parametrize("password", ["Password123", "wanderlust", "zzzzzzzzzzzz"])
def test_common_or_repetitive_passwords_are_rejected(password: str) -> None:
    with pytest.raises(ValueError, match="too"):
        validate_password_strength(password)


def test_reasonable_password_is_accepted() -> None:
    assert validate_password_strength("kyoto in the rain") == "kyoto in the rain"


@pytest.mark.parametrize(
    ("ip", "expected"),
    [
        ("203.0.113.77", "203.0.113.0/24"),
        ("2001:db8:abcd:12::1", "2001:db8:abcd::/48"),
        ("garbage", None),
    ],
)
def test_ip_prefix_never_keeps_full_address(ip: str, expected: str | None) -> None:
    assert ip_prefix(ip) == expected
