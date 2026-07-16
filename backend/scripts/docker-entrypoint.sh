#!/bin/sh
set -euo pipefail

echo "Running database migrations..."
alembic upgrade head

echo "Starting Career OS API..."
exec "$@"
