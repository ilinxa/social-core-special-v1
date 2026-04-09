# Social Media Advertising App

A social media advertising platform — monorepo with backend (Django REST API), frontend (Next.js), and mobile (React Native Expo).

## Structure
- `backend/` — Django 5.1 REST API (PostgreSQL, Redis, Celery)
- `frontend/` — Next.js web client (Next.js 16, React 19, Tailwind v4)
- `mobile/` — React Native Expo mobile app (planned)
- `docker/` — Nginx config, helper scripts
- `docker-compose.dev.yml` — Dev infrastructure (PostgreSQL + Redis)

## Environment
- `.env` loading priority: `backend/.env.dev` → `backend/.env` → `.env` (root)
- Key vars: DJANGO_SECRET_KEY, POSTGRES_*, REDIS_URL, AWS_*, GOOGLE_OAUTH_*, APPLE_OAUTH_*
- Generate secret key: `make secret-key`

## Development Environment
- IMPORTANT: Always use Docker (PostgreSQL + Redis) as the default development environment. Do NOT use SQLite.
- Settings: `backend_core.settings.local_docker` for dev/testing against Docker infra
- Start infra: `docker compose -f docker-compose.dev.yml up -d` (PostgreSQL 17 on :5432, Redis 7 on :6379)
- Run server: `DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker python manage.py runserver`
- Unit tests still use `backend_core.settings.local` (SQLite) for speed — this is acceptable for unit tests only
- Integration tests (`tests/api_integration/`) require live Docker server: `make test-api`

## Commands (Root Makefile)
- `make dev` — Django + Docker infra (PG + Redis) — **use this by default**
- `make local` — SQLite only, no Docker (avoid unless offline)
- `make test` — unit test suite (SQLite)
- `make test-api` — integration tests against Docker (PostgreSQL + Redis)
- `make check` — lint + tests (run before finishing any task)

## Pre-Commit Lint Rules
- IMPORTANT: Before every commit, run `black .`, `isort .`, and `flake8 .` from the `backend/` directory.
  CI (GitHub Actions) runs these checks and will fail if code is not formatted or has lint errors.
- `black .` — auto-formats Python code
- `isort .` — auto-sorts imports (compatible with black via pyproject.toml config)
- `flake8 .` — checks for unused imports (F401), unused variables (F841), redefinitions (F811), import order (E402)
- Fix all flake8 errors before committing — do NOT use `# noqa` unless there is a genuine reason
- For frontend: run `npm run lint` from the `frontend/` directory before committing frontend changes

## Documentation & Progress
- IMPORTANT: After each significant iteration, append a JSON entry to `progress/`.
  See `progress/README.md` for schema. Categories: planning, developing, testing,
  error-handling, bug-fixing, documentation, deployment, refactoring, reviewing.
- IMPORTANT: For new features follow: Describe → Plan → Review → Implement → Test → Document.
  Docs live in `docs/{descriptions,plans,implementations}/{workspace}/`.

## Permission-Aware API Responses (Tier 1.5)
- IMPORTANT: Every new app with detail views MUST embed `_permissions` into GET detail responses.
  Reference: `docs/plans/frontend/permission-aware-responses.md`
- Backend: Add `get_viewer_permissions()` staticmethod to Policy → add `PermissionInjectMixin` +
  set `self._inject_permissions = True` in `get()` on detail views only (never list/POST/PATCH).
- Frontend: Add `<Resource>Permissions` type → compose with `WithPermissions<T>` from `@/types/api`
  → gate UI elements with `<Can allowed={permissions.can_x}>` (`@/components/common/Can`).

## Explore / Search Integration (adding a new searchable entity)
- Reference implementation: `apps/explore/` (backend), `features/explore/` (frontend)
- Existing entities: **Business** (public, 11 filters) and **User** (auth-required, 5 filters)
- Backend: `ExploreSelector.search_<entity>()` (FTS `SearchVector` + `TrigramSimilarity` fallback,
  `Greatest()` combined, filter `> 0.01`) → slim serializer → `APIView` + `StandardPagination` view
  with `_extract_<entity>_params()` helper (`_parse_csv`, `_parse_bool`, `_parse_int`) → URL.
  View tests mock selector (SQLite-safe). Selector tests need `requires_postgres` marker.
- Frontend: types in `types/explore.ts` → `search<Entity>Api()` → queryKey → `useInfinite<Entity>Search()`
  (useInfiniteQuery + `getNextPage()`) → infinite scroll content (`useInView` → `fetchNextPage()`) →
  card component → filters component (reuse `CountrySelect`, `CityCombobox`, `TagInput`; enum values
  MUST match backend `TextChoices` exactly) → `FilterPanel` active-filter badge → `ExplorePage` tab
  with URL-synced params via `useMemo` + `updateUrl`.

## Feature Gate Integration (adding gates to new features)
- IMPORTANT: Every new backend app or feature MUST integrate with the Feature Gate System.
  This ensures the platform can be deployed in minimal (user-only), community (user+platform),
  or full (SaaS) configurations without code changes.
- Reference: `docs/implementations/backend/feature-gate-developer-guide.md`
- Core module: `apps/core/feature_config.py` (singleton, 10 public methods)

### Checklist
1. **System Gate (SG)** — new app/system: URL group `backend_core/urls/<system>.py` → register in
   `GATED_GROUPS` in `__init__.py` → guard Celery tasks + outcome handlers + admin `ready()` →
   add `systems.<name>: true` to both `deployment_config.json` AND `backend/conftest.py` `_FULL_FEATURE_CONFIG`.
2. **Module Gate (FG)** — toggle-able endpoint: `permission_classes = [IsAuthenticated, FeatureRequired("path")]`
   (static) or set + `self.check_permissions(self.request)` (method-level) → add to both config files.
3. **Sub-Feature Gate (FG)** — service-layer toggle: `if not feature_config.is_feature_enabled("path"): raise FeatureDisabled(feature="name")` → add to both config files.
4. **Limits (VG)** — numeric caps: `feature_config.check_limit("path", count, rule=..., resource=...)`
   or `FeatureConfig.effective_limit(config_limit, model_limit)` for dual-source → add to both config files (default 0 = unlimited).
5. **Config Values (VG)** — tunable constants: `feature_config.get_value("path", default)` → add to both config files.
6. **Tests**: `feature_config_override` fixture to disable gate → assert 403 / `FeatureDisabled` / `BusinessRuleViolation`.

### Key Rules
- `FeatureRequired("path")` returns a CLASS, not instance — this is a DRF requirement
- `is_system_enabled()` and `is_feature_enabled()` default to `False` (minimal deployment)
- `get_limit()` default 0 = unlimited. `get_value()` always needs explicit default
- SG gates are fixed at startup (URL registration). FG/VG can change at runtime via `reload()`
- ALWAYS add new paths to BOTH `deployment_config.json` AND `_FULL_FEATURE_CONFIG` in `backend/conftest.py`
- Test fixtures live in root `backend/conftest.py`, NOT in `backend/tests/conftest.py`

## Deployment Configuration
- IMPORTANT: The platform deployment is controlled by `deployment_config.json` (path set via `DEPLOYMENT_CONFIG_PATH` in settings).
  Missing file defaults to most restrictive state (user-only, all systems OFF). Always provide a config file.
- Reference: `docs/setup/deployment-configuration.md`
- Full annotated example: `docs/descriptions/backend/deployment_config_full_example.json`
- Three org modes: `"full"` (business + platform), `"user_and_platform"`, `"user_only"`
- When adding new features, update both `deployment_config.json` (dev default) and `docs/descriptions/backend/deployment_config_full_example.json` (annotated reference)

## Skills Mandates
- IMPORTANT: Use `project-documentation` skill for all feature documentation and progress tracking.
- IMPORTANT: Use `configuring-project-memory` skill when modifying CLAUDE.md or project memory.
- IMPORTANT: Use `skill-creator-pro` skill when creating or improving Claude skills.
- IMPORTANT: Use `ilinxa-frontend-standards` skill for all frontend code (React, Next.js, React Native).
