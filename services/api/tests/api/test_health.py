import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.redis import get_redis


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_every_response_carries_a_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert len(response.headers["x-request-id"]) >= 8


async def test_valid_upstream_request_id_is_propagated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "proxy-abc-12345"})

    assert response.headers["x-request-id"] == "proxy-abc-12345"


async def test_malformed_upstream_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "bad id\n<script>"})

    assert response.headers["x-request-id"] != "bad id\n<script>"


@pytest.mark.db
@pytest.mark.redis
@pytest.mark.usefixtures("migrated_db")
async def test_readiness_ok_when_database_and_redis_are_up(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "components": {"database": "ok", "redis": "ok"}}


class _BrokenRedis:
    async def ping(self) -> bool:
        raise ConnectionError("redis down")


@pytest.mark.db
@pytest.mark.usefixtures("migrated_db")
async def test_readiness_reports_unavailable_component(app: FastAPI, client: AsyncClient) -> None:
    app.dependency_overrides[get_redis] = lambda: _BrokenRedis()

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["components"] == {"database": "ok", "redis": "unavailable"}
    # Failure details stay in logs, never in the response.
    assert "redis down" not in response.text
