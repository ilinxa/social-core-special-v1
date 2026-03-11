# Setup Verification & Infrastructure Fixes — Implementation Reference

**Version:** v1
**Last Updated:** 2026-02-22
**Status:** Implemented

---

## 1. Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        3 Run Modes                                 │
├──────────────────┬──────────────────┬──────────────────────────────┤
│   Mode 1: Local  │ Mode 2: Hybrid   │ Mode 3: Full Docker          │
│                  │                  │                              │
│  ┌────────────┐  │  ┌────────────┐  │  ┌──────────────────────┐   │
│  │   Django    │  │  │   Django    │  │  │  django_app          │   │
│  │   (venv)    │  │  │   (venv)    │  │  │  (Gunicorn+Uvicorn)  │   │
│  └──────┬─────┘  │  └──────┬─────┘  │  └──────────┬───────────┘   │
│         │        │         │        │             │               │
│  ┌──────┴─────┐  │  ┌──────┴─────┐  │  ┌──────────┴───────────┐   │
│  │  SQLite    │  │  │ Docker     │  │  │  Docker              │   │
│  │            │  │  │ PG + Redis │  │  │  PG + Redis          │   │
│  └────────────┘  │  └────────────┘  │  └──────────────────────┘   │
│                  │                  │                              │
│  Settings:       │  Settings:       │  Settings:                   │
│  local.py        │  local_docker.py │  production.py               │
│  make local      │  make dev        │  make prod                   │
└──────────────────┴──────────────────┴──────────────────────────────┘
```

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UUID migration strategy | `SeparateDatabaseAndState` + raw SQL for PG, `schema_editor.alter_field` for SQLite | PostgreSQL cannot cast bigint→uuid; Django 5.1 uses identity columns not sequences; SQLite has no strict types |
| Docker health check | `python urllib.request` instead of `curl` | `python:3.12.9-slim-bookworm` does not include curl |
| Static/media paths | `/app/staticfiles` and `/app/media` | Must match Docker volume mount points in docker-compose.yml |
| Production image | Multi-stage build, non-root `django` user (UID 1000) | Security best practice; wheels built in builder stage, slim final image |
| Root `.env` for Docker testing | Separate from `backend/.env` | docker-compose.yml uses `env_file: .env` (root); needs localhost-friendly values (no SSL redirect, localhost in ALLOWED_HOSTS) |

## 3. Data Layer

### 3.1 Migration 0006: User.id BigAutoField → UUIDField

Location: `backend/apps/users/migrations/0006_alter_user_id.py`

**Prerequisite:** Migration 0005 clears all user-related data (users, profiles, tokens, sessions, OAuth connections, notifications).

**PostgreSQL path** (`_convert_postgres`):

| Step | SQL Operation | Why |
|------|--------------|-----|
| 1 | Query `pg_constraint` for FK constraints referencing `users` | Discover all 18+ FK dependencies dynamically |
| 2 | Query `pg_constraint` for CHECK constraints on `users` | Find `no_self_referral` CHECK that compares `id = referred_by_id` |
| 3 | Drop CHECK constraints | CHECK compares `id` (uuid) with `referred_by_id` (still bigint) — type mismatch error |
| 4 | Drop FK constraints | FK columns still bigint while `users.id` becomes uuid |
| 5 | Drop PK constraint | Required before type change on PK column |
| 6 | `DROP IDENTITY IF EXISTS` on `users.id` | Django 5.1 uses identity columns on PG (not sequences) — cannot change type while identity exists |
| 7 | `ALTER COLUMN id TYPE uuid USING gen_random_uuid()` | Cast bigint→uuid is impossible; generate new UUIDs |
| 8 | `SET DEFAULT gen_random_uuid()`, `SET NOT NULL` | Restore column properties |
| 9 | Convert `referred_by_id` to uuid (`USING NULL::uuid`) | Self-referencing FK column must match new PK type |
| 10 | Re-add PK, CHECK (`no_self_referral`), self-FK | Restore users table constraints |
| 11 | Convert FK columns in other tables + re-add FK constraints | All 17 external FK columns changed to uuid |

**SQLite path:** Uses `schema_editor.alter_field()` which recreates the table (SQLite's standard approach).

**State:** `SeparateDatabaseAndState` keeps Django's migration state in sync — `state_operations` has the `AlterField`, `database_operations` has the `RunPython`.

### Migrations Summary

| Migration | Purpose |
|-----------|---------|
| `users.0005_prepare_uuid_migration` | Clears all user data before type change |
| `users.0006_alter_user_id` | Converts `User.id` from BigAutoField to UUIDField |

## 4. Key Flows

### Flow 1: Mode 1 — Local Django + SQLite

1. Activate venv: `backend\venv\Scripts\activate`
2. `make local` (or `python manage.py runserver --settings=backend_core.settings.local`)
3. Migrations auto-apply with SQLite
4. Server runs at `http://localhost:8000`
5. Tests: `make test` (489 passed, 3 skipped — cache tests need Redis)

### Flow 2: Mode 2 — Django + Docker Infra

1. `make dev-up` → starts PostgreSQL 17 + Redis 7 via `docker-compose.dev.yml`
2. `make dev` → Django runs locally against Docker PG/Redis
3. Settings: `local_docker.py` (loads from `backend/.env.dev`)
4. Tests: `make test-docker` (492 passed, 0 skipped)

### Flow 3: Mode 3 — Full Docker Production Stack

1. Create root `.env` with localhost-friendly values
2. `make prod` → builds image, starts app + PG + Redis via `docker-compose.yml`
3. Entrypoint runs: `migrate --noinput` → `collectstatic --noinput` → `gunicorn`
4. Gunicorn with 4 Uvicorn workers on port 8000
5. WhiteNoise serves static files
6. `manage.py check --deploy` passes (warnings only, no errors)

### Flow 4: PostgreSQL UUID Migration

1. Migration 0005 clears all user data
2. Migration 0006 detects database vendor
3. PostgreSQL: raw SQL drops constraints → converts types → re-adds constraints
4. SQLite: `schema_editor.alter_field()` recreates table
5. Both paths leave Django state identical (UUIDField PK)

## 5. Configuration & Gotchas

### Environment Variables

| Variable | Mode 1 | Mode 2 | Mode 3 |
|----------|--------|--------|--------|
| `DJANGO_SETTINGS_MODULE` | `local` | `local_docker` | `production` |
| `POSTGRES_HOST` | N/A (SQLite) | `localhost` | `db` (Docker service) |
| `REDIS_URL` | N/A (DummyCache) | `redis://localhost:6379` | `redis://redis:6379` |
| `SECURE_SSL_REDIRECT` | N/A | N/A | `False` (local testing) |
| `ALLOWED_HOSTS` | `*` (DEBUG=True) | `*` (DEBUG=True) | `localhost,127.0.0.1,0.0.0.0` |

### Gotchas

- **Django 5.1 identity columns**: PostgreSQL uses identity columns instead of sequences. Must `DROP IDENTITY IF EXISTS` before changing column type. Previous Django versions used sequences which could just be dropped.
- **CHECK constraint type mismatch**: The `no_self_referral` CHECK (`id = referred_by_id`) fails during type conversion because PostgreSQL evaluates the expression when one column is uuid and the other is still bigint. Must drop CHECKs before any type changes.
- **Docker `curl` not available**: `python:3.12.9-slim-bookworm` does not include curl. Health checks must use Python's `urllib.request` instead.
- **`STATIC_ROOT` must match volume mount**: `production.py` sets `STATIC_ROOT = "/app/staticfiles"` which must match the Docker volume mount path `static_volume:/app/staticfiles`.
- **Dockerfile requirements path**: `production.txt` contains `-r base.txt` (relative import). Must copy the entire `requirements/` directory, not just `production.txt`.
- **Root `.env` vs `backend/.env`**: `docker-compose.yml` uses `env_file: .env` (root directory). `backend/.env` is for the Django process running locally. Don't confuse them.
- **Python version mismatch**: Dockerfile uses Python 3.12.9, local venv uses Python 3.11.4. No issues observed but worth noting for dependency compatibility.
- **pytest not in production image**: Test dependencies are in `local.txt`, not `production.txt`. Tests cannot run inside the production Docker container — run them locally or in a separate test container.

## 6. Testing

### Test Results

| Mode | Engine | Total | Passed | Skipped | Failed |
|------|--------|-------|--------|---------|--------|
| 1. Local (SQLite) | SQLite | 492 | 489 | 3 | 0 |
| 2. Hybrid (PG+Redis) | PostgreSQL 17 | 492 | 492 | 0 | 0 |
| 3. Full Docker | PostgreSQL 17 | N/A | N/A | N/A | N/A |

Mode 1 skips: 3 cache tests that require Redis.
Mode 3: pytest not installed in production image. Verified via `manage.py check --deploy` (0 errors, 34 warnings — all drf_spectacular cosmetic + expected SSL warning).

### Endpoint Verification (All 3 Modes)

| Endpoint | Expected | Result |
|----------|----------|--------|
| `GET /api/docs/` | 200 | 200 |
| `GET /api/schema/` | 200 | 200 |
| `GET /admin/` | 302 (→ login) | 302 |
| `POST /api/v1/auth/login/` | 400 (no credentials) | 400 |
| `GET /static/admin/css/base.css` | 200 | 200 (Mode 3 only, WhiteNoise) |

## 7. File Summary

### New Files

| File | Description |
|------|-------------|
| `.env` | Root environment file for local Docker testing (Mode 3) |

### Modified Files

| File | Change |
|------|--------|
| `backend/apps/users/migrations/0006_alter_user_id.py` | Rewrote with `SeparateDatabaseAndState` + raw SQL for PostgreSQL UUID conversion. Handles identity columns, FK/PK/CHECK constraints, self-referencing FK. |
| `backend/Dockerfile` | Fixed: copy full `requirements/` dir (not just `production.txt`), create `staticfiles`/`media` dirs with correct ownership, use `/app/entrypoint.sh` path, run `chmod` before `USER django` |
| `backend/backend_core/settings/production.py` | Fixed `STATIC_ROOT` from `/vol/static` → `/app/staticfiles`, `MEDIA_ROOT` from `/vol/media` → `/app/media` to match Docker volume mounts |
| `docker-compose.yml` | Changed health check from `curl` to `python urllib.request` (curl not in slim image) |

## 8. Known Limitations

1. **No test runner in production image**: pytest is dev-only. To run tests against PostgreSQL in Docker, use Mode 2 (`make test-docker`) or build a separate test image.
2. **drf_spectacular warnings**: 34 warnings about operationId collisions and missing serializer classes on RBAC/organization views. Cosmetic — API works correctly.
3. **`core` app model changes**: Django reported "Your models in app(s): 'core' have changes that are not yet reflected in a migration" — not investigated, pre-existing.

## 9. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Fix drf_spectacular warnings | Add `ENUM_NAME_OVERRIDES` and `serializer_class` to views | P2 |
| Investigate core app model drift | `core` has unapplied model changes | P1 |
| Add nginx service to docker-compose.yml | Currently commented out; needs SSL certs | P2 |
| Consider test Dockerfile | Separate `Dockerfile.test` that installs `local.txt` for CI | P1 |

## 10. Changelog

### v1 (2026-02-22)
- Verified all 3 run modes (local, hybrid, full Docker)
- Fixed UUID migration for PostgreSQL compatibility (identity columns, FK/PK/CHECK constraints)
- Fixed Dockerfile (requirements path, static dirs, entrypoint)
- Fixed production settings (STATIC_ROOT/MEDIA_ROOT paths)
- Fixed docker-compose health check (curl → python)
- Created root `.env` for local Docker testing
