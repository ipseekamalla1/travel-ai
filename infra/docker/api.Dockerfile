# syntax=docker/dockerfile:1.7
# FastAPI service + arq worker image. Build context: repository root.

FROM python:3.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /usr/local/bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# ---- development: deps incl. dev group; source is bind-mounted by compose ----
FROM base AS dev
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
COPY services/api/ ./
COPY infra/docker/api-entrypoint.sh /usr/local/bin/api-entrypoint
ENTRYPOINT ["api-entrypoint"]
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- production: runtime deps only, non-root ----
FROM base AS prod
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY services/api/ ./
RUN useradd --system --uid 10001 atu && chown -R atu /app
USER atu
EXPOSE 8000
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
