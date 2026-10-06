from collections.abc import AsyncIterator

import pytest
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.errors import FieldError, NotFoundError, ValidationFailedError
from app.main import create_app
from tests.conftest import make_settings


class _Payload(BaseModel):
    name: str = Field(min_length=1)
    nights: int = Field(ge=1)


def _probe_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/_probe")

    @router.post("/validate")
    async def validate(payload: _Payload) -> _Payload:
        return payload

    @router.get("/not-found")
    async def not_found() -> None:
        raise NotFoundError("Trip not found.")

    @router.get("/field-error")
    async def field_error() -> None:
        raise ValidationFailedError(
            errors=[FieldError(field="end_date", code="DATE_BEFORE_START", message="Too early.")]
        )

    @router.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail: db password=hunter2")

    return router


@pytest.fixture
async def probe_client() -> AsyncIterator[AsyncClient]:
    app: FastAPI = create_app(make_settings())
    app.include_router(_probe_router())
    # raise_app_exceptions=False lets us observe the 500 response instead of re-raising.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://testserver") as http,
    ):
        yield http


async def test_unknown_route_returns_problem_json(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["request_id"] == response.headers["x-request-id"]


async def test_request_validation_identifies_fields(probe_client: AsyncClient) -> None:
    response = await probe_client.post("/api/v1/_probe/validate", json={"name": "", "nights": 0})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert {e["field"] for e in body["errors"]} == {"name", "nights"}


async def test_app_error_maps_to_status_and_code(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/api/v1/_probe/not-found")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trip not found."


async def test_service_field_errors_are_preserved(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/api/v1/_probe/field-error")

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "end_date", "code": "DATE_BEFORE_START", "message": "Too early."}
    ]


async def test_unhandled_errors_do_not_leak_internals(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/api/v1/_probe/boom")

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text
