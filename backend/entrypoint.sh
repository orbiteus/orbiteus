#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn api:app --host 0.0.0.0 --port 8000 "$@"
