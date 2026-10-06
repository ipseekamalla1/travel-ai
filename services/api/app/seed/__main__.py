"""Deterministic development seed: `python -m app.seed` (or `make seed`).

Creates clearly-marked development data only. Idempotent: re-running updates the same rows.
Refuses to run in production.
"""

import asyncio
import os
import sys
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppEnv, get_settings
from app.core.db import create_engine, create_session_factory
from app.core.security import hash_password
from app.users.models import User
from app.users.repository import UserRepository

# Fixed IDs so seed data is reproducible across machines and resets.
DEV_USER_ID = uuid.UUID("01900000-0000-7000-8000-000000000001")
DEV_USER_EMAIL = "dev@example.com"
DEV_PASSWORD_ENV = "SEED_DEV_PASSWORD"  # noqa: S105 — env var name, not a secret


async def seed_users(db: AsyncSession, password: str) -> User:
    users = UserRepository(db)
    user = await users.get_by_id(DEV_USER_ID)
    if user is None:
        user = User(id=DEV_USER_ID, email=DEV_USER_EMAIL, display_name="[DEV] Dev Traveler")
        users.add(user)
    user.password_hash = hash_password(password)
    user.status = "active"
    return user


async def main() -> int:
    settings = get_settings()
    if settings.app_env in {AppEnv.PRODUCTION, AppEnv.STAGING}:
        print("Refusing to seed development data in", settings.app_env, file=sys.stderr)
        return 1
    password = os.environ.get(DEV_PASSWORD_ENV)
    if not password:
        print(f"Set {DEV_PASSWORD_ENV} (see .env.example) to seed the dev user.", file=sys.stderr)
        return 1

    engine = create_engine(settings)
    try:
        async with create_session_factory(engine)() as db:
            user = await seed_users(db, password)
            await db.commit()
    finally:
        await engine.dispose()
    print(f"Seeded dev user {user.email} (password from {DEV_PASSWORD_ENV}).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
