#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-4}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  backend_core.asgi:application


