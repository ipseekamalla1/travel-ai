"""Password hashing, session tokens and CSRF tokens (docs/SECURITY.md §2)."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2id with the library's RFC 9106 "low memory" profile (OWASP-compliant defaults).
_hasher = PasswordHasher()

# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

SESSION_TOKEN_BYTES = 32
CSRF_TOKEN_BYTES = 24


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-effort verification; a missing hash still costs one argon2 verify."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except VerifyMismatchError, VerificationError, InvalidHashError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> bytes:
    """Sessions are stored by SHA-256 of the token: a database leak doesn't yield usable cookies."""
    return hashlib.sha256(token.encode()).digest()


def _csrf_signature(nonce: str, secret: str) -> str:
    return hmac.new(secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()


def new_csrf_token(secret: str) -> str:
    """Signed double-submit token: `<nonce>.<hmac>`; the signature stops injected cookies."""
    nonce = secrets.token_urlsafe(CSRF_TOKEN_BYTES)
    return f"{nonce}.{_csrf_signature(nonce, secret)}"


def csrf_token_is_valid(cookie_token: str | None, header_token: str | None, secret: str) -> bool:
    if not cookie_token or not header_token:
        return False
    if not hmac.compare_digest(cookie_token, header_token):
        return False
    nonce, _, signature = cookie_token.partition(".")
    return bool(nonce) and hmac.compare_digest(signature, _csrf_signature(nonce, secret))
