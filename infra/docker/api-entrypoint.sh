#!/bin/sh
# Development entrypoint: apply migrations before starting the API.
# In production, migrations run as a separate release step (docs/DEPLOYMENT.md).
set -e

if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  echo "Applying database migrations..."
  alembic upgrade head
fi

exec "$@"
