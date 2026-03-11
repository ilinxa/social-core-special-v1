# Setup & Run Modes

## 3 Run Modes

| Mode | Settings | DB | Cache / Channels | Docker |
|------|----------|----|-------------------|--------|
| Local | `backend_core.settings.local` | SQLite | DummyCache / InMemory | No |
| Local Docker (hybrid) | `backend_core.settings.local_docker` | PostgreSQL | Redis | Infra only (PG + Redis) |
| Production | `backend_core.settings.production` | PostgreSQL | Redis | Full stack |

## Settings (`backend/backend_core/settings/`)

- `base.py` — Shared config (apps, DRF, JWT, Celery, OAuth, observability). Never used directly.
- `local.py` — SQLite, DummyCache, InMemory channels, Celery eager, console email, `DEBUG=True`.
- `local_docker.py` — PostgreSQL, Redis (cache + channels), `DEBUG=True`.
- `production.py` — PostgreSQL, Redis, SSL/HSTS, optional S3/R2, `DEBUG=False` with validation.

## Switching Modes

**Option A — Makefile (recommended):** Each target sets `DJANGO_SETTINGS_MODULE` automatically.

```
make local          # SQLite, no Docker
make dev            # Docker infra (PG + Redis) + local Django
make test           # pytest (SQLite by default)
make test-docker    # pytest against PostgreSQL
```

**Option B — manage.py:** Change the default on line 10-11 of `backend/manage.py`:

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
    # "backend_core.settings.local"        # uncomment for SQLite
    "backend_core.settings.local_docker"    # current default
)
```

## Requirements (`backend/requirements/`)

| File | Contents |
|------|----------|
| `base.txt` | Django 5.1, DRF, Daphne, Channels, psycopg2, Redis, Celery, PyJWT, structlog, boto3, Pillow |
| `local.txt` | base + dev tools (debug-toolbar, ipython, black, flake8, isort, pytest, factory-boy) |
| `production.txt` | base + whitenoise (optional sentry) |

## Virtual Environment

The venv lives at `backend/venv/`. Activate it before any Python/pip commands:

```bash
# Windows
backend\venv\Scripts\activate

# Linux/macOS
source backend/venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements/local.txt    # development
pip install -r backend/requirements/production.txt  # production
```
