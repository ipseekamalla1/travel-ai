from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select, update

from app.auth.models import Session
from app.workers.settings import delete_stale_sessions
from tests.helpers import register

pytestmark = [pytest.mark.db, pytest.mark.redis, pytest.mark.usefixtures("clean_state")]


async def test_delete_stale_sessions_removes_only_expired(
    app: FastAPI, client: AsyncClient
) -> None:
    await register(client, "a@example.com")
    await register(client, "b@example.com")
    async with app.state.session_factory() as db:
        oldest = await db.scalar(select(Session.id).order_by(Session.created_at).limit(1))
        await db.execute(
            update(Session)
            .where(Session.id == oldest)
            .values(expires_at=datetime.now(UTC) - timedelta(days=1))
        )
        await db.commit()
    ctx: dict[str, Any] = {
        "session_factory": app.state.session_factory,
        "settings": app.state.settings,
    }

    removed = await delete_stale_sessions(ctx)

    assert removed == 1
    async with app.state.session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Session)) == 1
