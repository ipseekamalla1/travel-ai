from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, update

from app.auth.models import Session
from app.core.security import hash_session_token
from app.users.models import User
from tests.helpers import API, TEST_PASSWORD, csrf_headers, login, post, register

pytestmark = [pytest.mark.db, pytest.mark.redis, pytest.mark.usefixtures("clean_state")]


def _second_client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


# ---------- registration ----------


async def test_register_creates_user_and_signs_in(client: AsyncClient) -> None:
    response = await register(client, "Maya@Example.Com", display_name="  Maya  ")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "maya@example.com"
    assert body["display_name"] == "Maya"
    assert "password" not in str(body).lower()
    assert client.cookies.get("atu_session")

    me = await client.get(f"{API}/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


async def test_session_cookie_is_http_only_and_same_site(client: AsyncClient) -> None:
    response = await register(client)

    session_cookie = next(
        h for h in response.headers.get_list("set-cookie") if h.startswith("atu_session=")
    )
    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie


async def test_session_token_is_stored_hashed(app: FastAPI, client: AsyncClient) -> None:
    await register(client)
    token = client.cookies["atu_session"]

    async with app.state.session_factory() as db:
        stored = await db.scalar(select(Session.token_hash))

    assert stored == hash_session_token(token)
    assert stored != token.encode()


async def test_register_rejects_duplicate_email_case_insensitively(client: AsyncClient) -> None:
    await register(client, "maya@example.com")

    response = await register(client, "MAYA@example.com")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "EMAIL_TAKEN"
    assert body["errors"][0]["field"] == "email"


@pytest.mark.parametrize(
    ("password", "expected_code"),
    [
        ("short", "STRING_TOO_SHORT"),
        ("password123", "VALUE_ERROR"),
        ("aaaaaaaaaaaa", "VALUE_ERROR"),
    ],
)
async def test_register_rejects_weak_passwords(
    client: AsyncClient, password: str, expected_code: str
) -> None:
    response = await register(client, password=password)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "password"
    assert response.json()["errors"][0]["code"] == expected_code


async def test_register_rejects_invalid_email_and_blank_name(client: AsyncClient) -> None:
    response = await register(client, "not-an-email", display_name="   ")

    assert response.status_code == 422
    assert {e["field"] for e in response.json()["errors"]} == {"email", "display_name"}


# ---------- CSRF ----------


async def test_unsafe_request_without_csrf_token_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": TEST_PASSWORD, "display_name": "A"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"


async def test_tampered_csrf_token_is_rejected(client: AsyncClient) -> None:
    forged = "nonce.0000"
    client.cookies.set("atu_csrf", forged)

    response = await client.post(
        f"{API}/auth/login",
        json={"email": "a@example.com", "password": TEST_PASSWORD},
        headers={"X-CSRF-Token": forged},
    )

    assert response.status_code == 403


async def test_untrusted_origin_is_rejected(client: AsyncClient) -> None:
    headers = await csrf_headers(client)

    response = await client.post(
        f"{API}/auth/login",
        json={"email": "a@example.com", "password": TEST_PASSWORD},
        headers={**headers, "Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"


async def test_trusted_web_origin_is_accepted(client: AsyncClient) -> None:
    headers = await csrf_headers(client)

    response = await client.post(
        f"{API}/auth/register",
        json={"email": "o@example.com", "password": TEST_PASSWORD, "display_name": "O"},
        headers={**headers, "Origin": "http://localhost:3000"},
    )

    assert response.status_code == 201


async def test_csrf_token_rotates_on_login(client: AsyncClient) -> None:
    await register(client, "rot@example.com")
    before = client.cookies["atu_csrf"]
    await post(client, "/auth/logout")

    await login(client, "rot@example.com")

    assert client.cookies["atu_csrf"] != before


# ---------- login ----------


async def test_login_succeeds_with_correct_password(app: FastAPI, client: AsyncClient) -> None:
    await register(client, "maya@example.com")

    async with _second_client(app) as fresh:
        response = await login(fresh, "MAYA@example.com")
        me = await fresh.get(f"{API}/auth/me")

    assert response.status_code == 200
    assert me.json()["email"] == "maya@example.com"


async def test_login_failures_do_not_reveal_whether_email_exists(
    app: FastAPI, client: AsyncClient
) -> None:
    await register(client, "maya@example.com")

    async with _second_client(app) as fresh:
        wrong_password = await login(fresh, "maya@example.com", "wrong-password-123")
        unknown_email = await login(fresh, "nobody@example.com")

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    def without_request_id(response: Response) -> dict[str, object]:
        return {k: v for k, v in response.json().items() if k != "request_id"}

    assert without_request_id(wrong_password) == without_request_id(unknown_email)


async def test_disabled_user_cannot_log_in_and_existing_session_stops_working(
    app: FastAPI, client: AsyncClient
) -> None:
    await register(client, "gone@example.com")
    async with app.state.session_factory() as db:
        await db.execute(update(User).values(status="disabled"))
        await db.commit()

    assert (await client.get(f"{API}/auth/me")).status_code == 401
    async with _second_client(app) as fresh:
        assert (await login(fresh, "gone@example.com")).status_code == 401


async def test_login_is_rate_limited_per_email(app: FastAPI, client: AsyncClient) -> None:
    # Default auth limit is 10/min; the per-email bucket allows half of that.
    responses = [await login(client, "target@example.com", "wrong-password-1") for _ in range(6)]

    assert [r.status_code for r in responses[:5]] == [401] * 5
    assert responses[5].status_code == 429
    assert responses[5].json()["code"] == "RATE_LIMITED"
    assert int(responses[5].headers["retry-after"]) > 0


# ---------- sessions ----------


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


async def test_garbage_session_cookie_is_unauthenticated(client: AsyncClient) -> None:
    client.cookies.set("atu_session", "not-a-real-token")

    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_logout_revokes_the_session_server_side(client: AsyncClient) -> None:
    await register(client)
    stolen_token = client.cookies["atu_session"]

    response = await post(client, "/auth/logout")

    assert response.status_code == 204
    client.cookies.set("atu_session", stolen_token)
    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_logout_is_idempotent_without_a_session(client: AsyncClient) -> None:
    await csrf_headers(client)

    assert (await post(client, "/auth/logout")).status_code == 204


async def test_logout_all_revokes_every_session(app: FastAPI, client: AsyncClient) -> None:
    await register(client, "multi@example.com")
    async with _second_client(app) as phone:
        await login(phone, "multi@example.com")
        assert (await phone.get(f"{API}/auth/me")).status_code == 200

        assert (await post(client, "/auth/logout-all")).status_code == 204

        assert (await phone.get(f"{API}/auth/me")).status_code == 401
    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_expired_session_is_rejected(app: FastAPI, client: AsyncClient) -> None:
    await register(client)
    async with app.state.session_factory() as db:
        await db.execute(
            update(Session).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db.commit()

    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_activity_extends_idle_expiry_but_not_past_absolute(
    app: FastAPI, client: AsyncClient
) -> None:
    await register(client)
    soon = datetime.now(UTC) + timedelta(hours=1)
    async with app.state.session_factory() as db:
        await db.execute(
            update(Session).values(
                last_seen_at=datetime.now(UTC) - timedelta(hours=1),
                expires_at=soon,
                absolute_expires_at=soon + timedelta(minutes=30),
            )
        )
        await db.commit()

    assert (await client.get(f"{API}/auth/me")).status_code == 200

    async with app.state.session_factory() as db:
        refreshed = await db.scalar(select(Session))
    assert refreshed is not None
    assert refreshed.expires_at == refreshed.absolute_expires_at
