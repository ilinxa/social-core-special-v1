# Run Modes — Detailed Reference

**Last Updated:** 2026-02-22
**Status:** All 3 modes tested and verified

---

The backend supports 3 run modes, each targeting a different development scenario. All 3 share the same Django codebase — only the settings module and infrastructure differ.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Settings Inheritance                                 │
│                                                                             │
│                          base.py                                            │
│                        (shared config)                                      │
│                       /      |       \                                      │
│                      /       |        \                                     │
│              local.py  local_docker.py  production.py                       │
│              Mode 1       Mode 2          Mode 3                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Mode 1: Local (SQLite, No Docker)

**Purpose:** Fastest iteration cycle. Zero infrastructure dependencies. Good for quick feature development, offline work, and running tests.

**Settings:** `backend_core.settings.local`

### How It Works

```
┌─────────────────────────────────┐
│         Your Machine            │
│                                 │
│  ┌──────────────────────────┐   │
│  │    Django (venv)          │   │
│  │    runserver :8000        │   │
│  │    DEBUG = True           │   │
│  └─────────┬────────────────┘   │
│            │                    │
│  ┌─────────┴────────────────┐   │
│  │    SQLite                 │   │
│  │    backend_core/db.sqlite3│   │
│  └──────────────────────────┘   │
│                                 │
│  Cache:     DummyCache (none)   │
│  Channels:  InMemoryChannelLayer│
│  Celery:    ALWAYS_EAGER (sync) │
│  Email:     Console backend     │
│  CORS:      Allow all origins   │
└─────────────────────────────────┘
```

### How to Run

```bash
# Activate virtual environment
backend\venv\Scripts\activate          # Windows
source backend/venv/bin/activate       # Linux/macOS

# Start server
make local
# Or manually:
python backend/manage.py runserver --settings=backend_core.settings.local
```

### Configuration Details

| Setting | Value |
|---------|-------|
| `DEBUG` | `True` |
| `ALLOWED_HOSTS` | `localhost, 127.0.0.1, 0.0.0.0, [::1], testserver` |
| Database | SQLite at `backend/backend_core/db.sqlite3` |
| Cache | `DummyCache` (no caching) |
| Channel Layer | `InMemoryChannelLayer` (single-process only) |
| Sessions | Database-backed (`django.contrib.sessions.backends.db`) |
| Celery | `ALWAYS_EAGER=True` — tasks run synchronously |
| Email | Console backend (prints to terminal) |
| CORS | `CORS_ALLOW_ALL_ORIGINS=True` |
| Static Files | `backend/backend_core/staticfiles/` |
| Media Files | `backend/backend_core/media/` |
| Debug Toolbar | Enabled if `debug_toolbar` is in `INSTALLED_APPS` |
| Logging Level | `DEBUG` for requests and channels |

### Environment File

None required. All defaults are hardcoded in `local.py`.

### Dependencies

```bash
pip install -r backend/requirements/local.txt
```

Includes `base.txt` plus dev tools: django-debug-toolbar, ipython, black, flake8, isort, pytest, pytest-django, factory-boy.

### Limitations

- No caching — `DummyCache` means cache.set/get are no-ops
- No real WebSocket support — `InMemoryChannelLayer` only works within a single process
- No Redis — 3 cache-related tests are skipped
- SQLite lacks some PostgreSQL features (JSON operators, full-text search, advisory locks)
- Celery tasks run synchronously — no async/delayed execution

### Test Results (Verified 2026-02-22)

| Metric | Result |
|--------|--------|
| Total tests | 492 |
| Passed | 489 |
| Skipped | 3 (cache tests, need Redis) |
| Failed | 0 |
| Endpoints | All responding correctly |

---

## Mode 2: Hybrid (Django Local + Docker PG/Redis)

**Purpose:** Production-like database and cache without containerizing Django. Best balance of realistic infrastructure and fast Django iteration (no image rebuilds on code change).

**Settings:** `backend_core.settings.local_docker`

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                       Your Machine                               │
│                                                                  │
│  ┌──────────────────────────┐                                    │
│  │    Django (venv)          │                                    │
│  │    runserver :8000        │                                    │
│  │    DEBUG = True           │                                    │
│  └─────────┬────────┬───────┘                                    │
│            │        │                                            │
│     ┌──────┘        └──────┐                                     │
│     │                      │                                     │
│  ┌──┴──────────────┐  ┌────┴────────────────┐                    │
│  │  Docker         │  │  Docker              │                   │
│  │  PostgreSQL 17  │  │  Redis 7             │                   │
│  │  :5432          │  │  :6379               │                   │
│  │  dev_postgres   │  │  dev_redis           │                   │
│  └─────────────────┘  └─────────────────────┘                    │
│                                                                  │
│  Compose file: docker-compose.dev.yml                            │
│  Network: dev_network (bridge)                                   │
└──────────────────────────────────────────────────────────────────┘
```

### How to Run

```bash
# Activate virtual environment
backend\venv\Scripts\activate          # Windows
source backend/venv/bin/activate       # Linux/macOS

# Start infrastructure + Django
make dev
# Or manually:
docker compose -f docker-compose.dev.yml up -d
python backend/manage.py runserver --settings=backend_core.settings.local_docker
```

### Configuration Details

| Setting | Value |
|---------|-------|
| `DEBUG` | `True` |
| `ALLOWED_HOSTS` | `localhost, 127.0.0.1, 0.0.0.0, [::1]` |
| Database | PostgreSQL 17 at `localhost:5432` (DB: `backend_core_db`, user: `django_user`) |
| Cache | Redis at `redis://localhost:6379/1` (key prefix: `dev`) |
| Channel Layer | `RedisChannelLayer` at `localhost:6379` |
| Sessions | Redis-backed (`django.contrib.sessions.backends.cache`) |
| Celery | Default (async, requires broker) |
| CORS | `CORS_ALLOW_ALL_ORIGINS=True` |
| Static Files | `backend/backend_core/staticfiles/` |
| Media Files | `backend/backend_core/media/` |
| Connection Pooling | `CONN_MAX_AGE=60` (1 minute) |

### Environment File

`backend/.env.dev` — loaded by Django (via python-dotenv).

```
POSTGRES_DB=backend_core_db
POSTGRES_USER=django_user
POSTGRES_PASSWORD=postgres_dev_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Docker Services (docker-compose.dev.yml)

| Service | Container | Image | Port | Healthcheck |
|---------|-----------|-------|------|-------------|
| `postgres` | `dev_postgres` | `postgres:17-alpine` | `5432:5432` | `pg_isready` |
| `redis` | `dev_redis` | `redis:7-alpine` | `6379:6379` | `redis-cli ping` |
| `nginx` | `dev_nginx` | `nginx:1.25-alpine` | `80:80` | Optional (`--profile nginx`) |

Data: PostgreSQL data persisted in `postgres_dev_data` volume. Redis is ephemeral (no volume by default).

### Useful Commands

```bash
# Database shell
docker exec -it dev_postgres psql -U django_user -d backend_core_db

# Redis CLI
docker exec -it dev_redis redis-cli

# Stop infrastructure (keep data)
make dev-down
# Or: docker compose -f docker-compose.dev.yml down

# Stop infrastructure + delete all data
docker compose -f docker-compose.dev.yml down -v
```

### Limitations

- Ports 5432 and 6379 must be free on host machine
- Django still runs locally — code changes reflect instantly (no rebuild), but it's not testing the Docker image/entrypoint
- No SSL, no WhiteNoise, no gunicorn — uses Django's dev server

### Test Results (Verified 2026-02-22)

| Metric | Result |
|--------|--------|
| Total tests | 492 |
| Passed | 492 |
| Skipped | 0 |
| Failed | 0 |
| Endpoints | All responding correctly |

---

## Mode 3: Full Docker (Production Stack)

**Purpose:** Tests the full production deployment pipeline — Docker image build, entrypoint script, gunicorn, collectstatic, migrations, networking. Use this to verify the app works exactly as it will in production.

**Settings:** `backend_core.settings.production`

### How It Works

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Docker Engine                                      │
│                                                                           │
│  ┌──────────────────────────────────────────┐                             │
│  │  django_app                               │                            │
│  │  Image: django-backend:latest             │                            │
│  │  Python 3.12.9-slim-bookworm              │                            │
│  │  User: django (UID 1000)                  │                            │
│  │                                           │                            │
│  │  Entrypoint:                              │                            │
│  │    1. migrate --noinput                   │                            │
│  │    2. collectstatic --noinput             │                            │
│  │    3. gunicorn (4 Uvicorn workers)        │                            │
│  │                                           │                            │
│  │  Ports: 8000:8000                         │                            │
│  │  Volumes: /app/staticfiles, /app/media    │                            │
│  │  Networks: frontend, backend              │                            │
│  └─────────────┬───────────┬─────────────────┘                            │
│                │           │                                              │
│         ┌──────┘           └──────┐                                       │
│         │                         │                                       │
│  ┌──────┴──────────────┐  ┌───────┴─────────────────┐                     │
│  │  postgres_db         │  │  redis_cache             │                    │
│  │  postgres:17-alpine  │  │  redis:7-alpine          │                    │
│  │  Networks:           │  │  Network: backend         │                   │
│  │    backend, database │  │  Volume: redis_prod_data  │                   │
│  │  Volume:             │  └─────────────────────────┘                    │
│  │    postgres_prod_data│                                                 │
│  └─────────────────────┘                                                  │
│                                                                           │
│  Compose: docker-compose.yml                                              │
│  Networks: frontend (bridge), backend (bridge), database (internal)       │
└───────────────────────────────────────────────────────────────────────────┘
```

### How to Run

```bash
# Start the full stack (builds image + starts all containers)
make prod

# Or manually:
docker compose up -d --build
```

### Configuration Details

| Setting | Value |
|---------|-------|
| `DEBUG` | `False` (asserted) |
| `ALLOWED_HOSTS` | From `ALLOWED_HOSTS` env var (validated, no wildcards) |
| Database | PostgreSQL 17 at `db:5432` (Docker service name) |
| Cache | Redis at `redis://redis:6379/1` (key prefix: `prod`) |
| Channel Layer | `RedisChannelLayer` at `redis://redis:6379` |
| Sessions | Redis-backed, 1 day TTL |
| WSGI/ASGI Server | Gunicorn 23.0 with 4 Uvicorn workers |
| Static Files | WhiteNoise (compressed, 1-year cache), collected to `/app/staticfiles` |
| Media Files | Filesystem at `/app/media` (or S3/R2 if `USE_S3=true`) |
| Connection Pooling | `CONN_MAX_AGE=600` (10 minutes) |
| CORS | Explicit origins from `CORS_ALLOWED_ORIGINS` env var |
| Email | SMTP backend (configurable via env vars) |

### Security (Production Hardening)

| Feature | Value |
|---------|-------|
| `SECURE_SSL_REDIRECT` | `True` (override with env var for local testing) |
| `SESSION_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_HTTPONLY` | `True` |
| `X_FRAME_OPTIONS` | `DENY` |
| `SECURE_HSTS_SECONDS` | `31536000` (1 year) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` |
| `SECURE_HSTS_PRELOAD` | `True` |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` |
| `SECURE_BROWSER_XSS_FILTER` | `True` |
| `SECURE_PROXY_SSL_HEADER` | `X-Forwarded-Proto: https` |

### Environment File

Root `.env` — loaded by docker-compose.yml via `env_file: .env`.

For local Docker testing:

```
DJANGO_SETTINGS_MODULE=backend_core.settings.production
DJANGO_SECRET_KEY=<generate-a-strong-key>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
POSTGRES_DB=backend_core_db
POSTGRES_USER=django_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
USE_S3=false
SECURE_SSL_REDIRECT=False
```

For real production: use `.env.example` as template, set real domain in `ALLOWED_HOSTS`, enable `SECURE_SSL_REDIRECT=True`, use strong secrets.

### Docker Image (Dockerfile)

Multi-stage build:

| Stage | Base Image | Purpose |
|-------|------------|---------|
| `builder` | `python:3.12.9-slim-bookworm` | Install pip, build wheels from `requirements/production.txt` |
| Final | `python:3.12.9-slim-bookworm` | Copy wheels, install, copy app code, create `django` user |

Key details:
- Non-root user: `django` (UID/GID 1000)
- Static/media dirs created with correct ownership: `/app/staticfiles`, `/app/media`
- Entrypoint: `/app/entrypoint.sh`
- No `curl` in image — health check uses `python urllib.request`

### Docker Services (docker-compose.yml)

| Service | Container | Image | Ports | Networks | Volumes | Healthcheck |
|---------|-----------|-------|-------|----------|---------|-------------|
| `app` | `django_app` | `django-backend:latest` | `8000:8000` | frontend, backend | `static_volume`, `media_volume` | `python urllib` → `/admin/` |
| `db` | `postgres_db` | `postgres:17-alpine` | none (internal) | backend, database | `postgres_prod_data` | `pg_isready` |
| `redis` | `redis_cache` | `redis:7-alpine` | none (internal) | backend | `redis_prod_data` | `redis-cli ping` |
| `nginx` | (commented) | `nginx:1.25-alpine` | `80, 443` | frontend | static, media, ssl, certbot | — |

### Networks

| Network | Type | Services | Purpose |
|---------|------|----------|---------|
| `frontend_network` | bridge | app, (nginx) | Public-facing traffic |
| `backend_network` | bridge | app, db, redis | Internal app-to-infra |
| `database` | bridge (internal) | db | Database-only, no external access |

### Entrypoint Flow

```
Container starts
    │
    ├─ 1. python manage.py migrate --noinput
    │     └─ Applies all pending migrations to PostgreSQL
    │
    ├─ 2. python manage.py collectstatic --noinput
    │     └─ Collects 163 static files to /app/staticfiles (469 post-processed by WhiteNoise)
    │
    └─ 3. exec gunicorn
          --bind 0.0.0.0:8000
          --workers 4
          --worker-class uvicorn.workers.UvicornWorker
          backend_core.asgi:application
          └─ ASGI app via Gunicorn + Uvicorn (supports HTTP + WebSocket)
```

### Useful Commands

```bash
# View logs
make prod-logs
# Or: docker compose logs -f

# Django shell inside container
make prod-shell
# Or: docker compose exec app python manage.py shell

# Bash inside container
make prod-bash
# Or: docker compose exec app /bin/sh

# Run Django deploy checks
docker compose exec app python manage.py check --deploy

# Stop stack (keep volumes)
make prod-down
# Or: docker compose down

# Stop stack + delete all data
docker compose down -v
```

### Limitations

- No pytest in production image — test dependencies are dev-only (`local.txt`)
- No nginx enabled by default — uncomment in docker-compose.yml and provide SSL certs
- No Celery worker container — add separately when needed
- Health check start period is 40s — first check may take up to 70s total

### Test Results (Verified 2026-02-22)

| Metric | Result |
|--------|--------|
| Image build | Successful |
| Migrations | 56 applied, all OK |
| collectstatic | 163 files, 469 post-processed |
| Gunicorn | 4 workers started |
| Health check | Healthy |
| `check --deploy` | 0 errors, 34 warnings (drf_spectacular cosmetic + expected SSL) |
| Endpoints | All responding correctly |

---

## Mode Comparison

| Aspect | Mode 1: Local | Mode 2: Hybrid | Mode 3: Full Docker |
|--------|---------------|----------------|---------------------|
| **Settings** | `local.py` | `local_docker.py` | `production.py` |
| **Command** | `make local` | `make dev` | `make prod` |
| **Database** | SQLite | PostgreSQL 17 (Docker) | PostgreSQL 17 (Docker) |
| **Cache** | DummyCache | Redis 7 (Docker) | Redis 7 (Docker) |
| **Channels** | InMemory | Redis | Redis |
| **Server** | Django runserver | Django runserver | Gunicorn + Uvicorn |
| **Static Files** | Django serves | Django serves | WhiteNoise |
| **DEBUG** | True | True | False |
| **Docker needed** | No | Infra only | Full stack |
| **Code changes** | Instant (auto-reload) | Instant (auto-reload) | Requires rebuild |
| **Startup time** | ~2s | ~5s (+ container start) | ~30s (build + start) |
| **Tests** | 489 passed, 3 skipped | 492 passed, 0 skipped | N/A (no pytest) |
| **Best for** | Quick iteration, offline | Realistic dev, full tests | Deployment verification |

## When to Use Each Mode

| Scenario | Recommended Mode |
|----------|-----------------|
| Writing new feature code | Mode 1 (fastest iteration) |
| Running full test suite | Mode 2 (all tests pass, real PG/Redis) |
| Testing specific DB behavior (migrations, constraints, JSON) | Mode 2 |
| Testing WebSocket features | Mode 2 (real Redis channel layer) |
| Testing caching behavior | Mode 2 (real Redis cache) |
| Verifying Docker build works | Mode 3 |
| Testing production settings (security, WhiteNoise, gunicorn) | Mode 3 |
| Pre-deployment smoke test | Mode 3 |
| CI/CD pipeline | Mode 2 for tests, Mode 3 for build verification |
| Offline / no Docker available | Mode 1 |
