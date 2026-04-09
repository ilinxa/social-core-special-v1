#!/bin/bash
# =============================================================================
# E2E Backend Entrypoint
# =============================================================================
# 1. Wait for PostgreSQL to accept connections
# 2. Run Django migrations
# 3. Collect static files
# 4. Start Daphne ASGI server (NOT gunicorn — WebSocket support required)
# =============================================================================

set -e

echo "=== E2E Backend Entrypoint ==="

# --- Wait for PostgreSQL ---
echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}..."
MAX_RETRIES=30
RETRY=0
until python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
s.connect(('${POSTGRES_HOST:-localhost}', ${POSTGRES_PORT:-5432}))
s.close()
" 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "ERROR: PostgreSQL not available after ${MAX_RETRIES} retries"
        exit 1
    fi
    echo "  Retry $RETRY/$MAX_RETRIES..."
    sleep 2
done
echo "PostgreSQL is ready."

# --- Run Migrations ---
echo "Running Django migrations..."
python manage.py migrate --noinput
echo "Migrations complete."

# --- Collect Static Files ---
echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true
echo "Static files collected."

# --- Start Daphne ASGI Server ---
echo "Starting Daphne ASGI server on 0.0.0.0:8000..."
exec daphne \
    -b 0.0.0.0 \
    -p 8000 \
    --proxy-headers \
    backend_core.asgi:application
