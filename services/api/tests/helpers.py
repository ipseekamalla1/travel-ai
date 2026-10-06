"""Shared test helpers for authenticated API calls."""

from httpx import AsyncClient, Response

API = "/api/v1"
# Test-only credential used by factories and auth tests.
TEST_PASSWORD = "correct-horse-battery-7"


async def csrf_headers(client: AsyncClient) -> dict[str, str]:
    """Fetch (and store as a cookie) a CSRF token, returning the matching header."""
    response = await client.get(f"{API}/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def register(
    client: AsyncClient,
    email: str = "maya@example.com",
    *,
    password: str = TEST_PASSWORD,
    display_name: str = "Maya",
) -> Response:
    return await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
        headers=await csrf_headers(client),
    )


async def login(client: AsyncClient, email: str, password: str = TEST_PASSWORD) -> Response:
    return await client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        headers=await csrf_headers(client),
    )


async def post(client: AsyncClient, path: str, **kwargs: object) -> Response:
    """POST with the client's current CSRF cookie echoed in the header."""
    token = client.cookies.get("atu_csrf")
    headers = {"X-CSRF-Token": token} if token else {}
    return await client.post(f"{API}{path}", headers=headers, **kwargs)  # type: ignore[arg-type]
