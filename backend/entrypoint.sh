#!/bin/bash
set -e

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput 2>/dev/null || true

# Dynamic worker count: 2 * CPU cores + 1, capped at [1, 8]
CPU_COUNT=$(nproc 2>/dev/null || echo 2)
WORKERS=${UVICORN_WORKERS:-$(( (CPU_COUNT * 2 + 1) < 8 ? (CPU_COUNT * 2 + 1) : 8 ))}
# Enforce minimum 1
if [ "$WORKERS" -lt 1 ]; then WORKERS=1; fi

echo "=== Starting Uvicorn (ASGI) with ${WORKERS} workers ==="
exec python -m uvicorn apitester.asgi:application \
    --host "0.0.0.0" \
    --port "${PORT:-8000}" \
    --workers "$WORKERS" \
    --access-logfile - \
    --error-logfile -
