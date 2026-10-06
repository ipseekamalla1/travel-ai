import asyncio

import asyncpg
import pytest
from alembic import command
from sqlalchemy.engine import make_url

from tests.conftest import TEST_DATABASE_URL, alembic_config

pytestmark = pytest.mark.db


async def _installed_extensions() -> set[str]:
    url = make_url(TEST_DATABASE_URL)
    conn = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=url.database,
    )
    try:
        rows = await conn.fetch("SELECT extname FROM pg_extension")
        return {row["extname"] for row in rows}
    finally:
        await conn.close()


@pytest.mark.usefixtures("migrated_db")
async def test_head_enables_required_extensions() -> None:
    assert {"citext", "pg_trgm", "vector"} <= await _installed_extensions()


@pytest.mark.usefixtures("migrated_db")
async def test_migrations_round_trip() -> None:
    cfg = alembic_config()
    await asyncio.to_thread(command.downgrade, cfg, "base")
    await asyncio.to_thread(command.upgrade, cfg, "head")

    assert {"citext", "pg_trgm", "vector"} <= await _installed_extensions()
