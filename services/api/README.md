# atu-api

FastAPI service for AI Travel Universe. See the root [README](../../README.md) and
[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md#4-backend-architecture).

```bash
uv sync                                  # install
uv run fastapi dev app/asgi.py           # run (needs Postgres + Redis, see root README)
uv run alembic upgrade head              # migrate
uv run pytest                            # test
uv run ruff check . && uv run mypy app tests
```
