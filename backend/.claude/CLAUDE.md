# Backend — Django REST API

## Architecture
- Django 5.1 + DRF. PostgreSQL via psycopg2. Redis for cache + Channels + Celery broker.
- Settings: 4-tier split in `backend_core/settings/` — base, local, local_docker, production.
  - `local` = SQLite, no Docker. Default for tests.
  - `local_docker` = PostgreSQL + Redis on localhost. Use for dev with real infra.
  - `production` = SSL, security hardening, S3 storage. NEVER use locally.
  - `base` = shared config imported by all others. Never use directly.
- Apps in `apps/`. Each is self-contained: models, views, serializers, tests/.
- Hybrid workflow: Django runs locally, infra (PG + Redis) in Docker via `make dev-up`.

## Setup & Running
- Virtual environment at `./venv/` — activate before any pip/python command.
- `manage.py` defaults to `local_docker`. To switch, change line 10-11 or set
  `DJANGO_SETTINGS_MODULE` env var. The Makefile handles this automatically per target.
- Use the Makefile. Don't run `python manage.py` directly unless you set the settings module.
- See `docs/setup/setup-and-run-modes.md` for full details.

## Hard Rules

### Core Rules
- IMPORTANT: Custom User model (`apps.users.User`). Never import
  `django.contrib.auth.models.User`. Always use `get_user_model()` or
  `settings.AUTH_USER_MODEL` in ForeignKeys.
- IMPORTANT: All endpoints default to `IsAuthenticated`. Override explicitly
  with `permission_classes = [AllowAny]` only for public endpoints.
- IMPORTANT: Never hand-edit migration files. Always use `makemigrations`.
- Never use `local` or `local_docker` settings in production.
  Set `DJANGO_SETTINGS_MODULE=backend_core.settings.production`.
### Dependencies
- IMPORTANT: When adding a new dependency, add it to the correct file in `requirements/`:
  - `base.txt` — packages needed in ALL environments (Django, DRF, Celery, etc.)
  - `local.txt` — dev-only packages (testing, linting, debugging tools)
  - `production.txt` — production-only packages (whitenoise, sentry, etc.)
  Never install a package without recording it. Never add dev-only packages to `base.txt`.
### Settings
- IMPORTANT: Settings are split across 4 files in `backend_core/settings/`. Understand which
  file to edit:
  - `base.py` — shared config (INSTALLED_APPS, DRF, middleware, Celery, JWT, etc.)
  - `local.py` — SQLite, no Docker overrides only
  - `local_docker.py` — PostgreSQL + Redis overrides only
  - `production.py` — production hardening only
  Never put environment-specific config in `base.py` (e.g., DB credentials, DEBUG).
  Never put shared config in environment files (e.g., INSTALLED_APPS, REST_FRAMEWORK).
### App Creation
- IMPORTANT: New apps in `apps/` only. Must include tests/ with conftest.py and factories.py.
- IMPORTANT: Models MUST inherit from `apps.core.models.TimeStampedModel` or `UUIDModel`.
- IMPORTANT: Add to `INSTALLED_APPS` in `backend_core/settings/base.py` with full path.

## Skills Mandates
- IMPORTANT: Use `django-app-creator` skill when creating or modifying Django apps. Never put business logic in views, serializers, signals, or models.
- IMPORTANT: Use `django-observability` skill for all logging, metrics, and audit trails. Never use print(), bare logging.getLogger(), or custom audit logic.
- IMPORTANT: Use `django-testing` skill for all tests. pytest only, never Django TestCase. 80% minimum coverage.
- IMPORTANT: Use `django-notifications` skill for all user notifications. Never send emails directly via EmailService unless it's a non-user notification.
- IMPORTANT: Use `rbac-integration-skill` for all authorization. Never hand-roll permission checks or query RolePermission directly.
- IMPORTANT: Use `project-documentation` skill for implementation docs. Follow the backend template variant.

## After Any Change
Run `make check`. If you modified any model, run `make makemigrations` and
verify no unexpected migration was generated.

## Apps
| App | Purpose |
|-----|---------|
| core | Base models (TimeStampedModel, UUIDModel), pagination, permissions, observability, feature gates |
| users | User profiles, avatar uploads |
| auth | JWT (15min access / 7day refresh), OAuth (Google/Apple), device sessions |
| email | Templates, AWS SES/SNS webhooks, tracking |
| notifications | Multi-channel: email, push, in-app; scoped preferences; org-broadcast |
| organization | Multi-tenant platform + business accounts, profiles, lifecycle management |
| rbac | Roles (level-based hierarchy), permissions, memberships, policy-based authorization |
| transaction | State machine: invitations, requests, approvals, ownership transfers (14 types) |
| forms | Dynamic form builder, versioned templates, form-transaction integration |
| network | Follow + connection system, polymorphic (user/business/platform) |
| chat | Real-time messaging: 20 REST endpoints + WebSocket (ChatConsumer), scope isolation |
| cms | Content management: draft/publish, API key auth, media management |
| explore | FTS + trigram search, 5 endpoints, SuggestedTag autocomplete |

## API
- Base: `/api/v1/` — URL path versioning
- Docs: `/api/docs/` (Swagger), `/api/schema/` (OpenAPI)
- Auth: `/api/v1/auth/login/` (POST → tokens), `/api/v1/auth/refresh/`, `/api/v1/auth/logout/`

## WebSockets
- ASGI via Daphne. Channel layer: InMemory (local) / Redis (docker + production).
- Add consumers in the relevant app, register routes in `backend_core/routing.py`.
