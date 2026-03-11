# Social Media Advertising App

A social media advertising platform — monorepo with backend (Django REST API), frontend (Next.js), and mobile (React Native Expo).

## Structure
- `backend/` — Django 5.1 REST API (PostgreSQL, Redis, Celery)
- `frontend/` — Next.js web client (planned)
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

## Documentation & Progress
- IMPORTANT: After each significant iteration, append a JSON entry to `progress/`.
  See `progress/README.md` for schema. Categories: planning, developing, testing,
  error-handling, bug-fixing, documentation, deployment, refactoring, reviewing.
- IMPORTANT: For new features follow: Describe → Plan → Review → Implement → Test → Document.
  Docs live in `docs/{descriptions,plans,implementations}/{workspace}/`.

## Compaction
When compacting, preserve: exact file paths of all modified files, current
migration state, and any error messages encountered during this session.

## Permission-Aware API Responses (Tier 1.5)
- IMPORTANT: Every new app with detail views MUST integrate the Permission-Aware Responses system.
  This embeds `_permissions` (evaluated RBAC booleans) into GET detail responses so the frontend
  can gate UI elements (edit buttons, panels, danger zones) without extra API calls.
- Reference implementation: `docs/plans/frontend/permission-aware-responses.md`

### Backend Integration Checklist
1. **Policy**: Add `get_viewer_permissions(*, ...)` staticmethod returning `dict[str, bool]`.
   - For user+resource policies (like BusinessPolicy): return booleans directly.
   - For exception-raising policies (like FormTemplatePolicy): use `_safe_check()` wrapper to convert exceptions to `False`.
2. **Views**: Add `PermissionInjectMixin` (from `apps.core.views`) to detail views.
   - Set `policy_class`, implement `_build_policy_kwargs()`, set `self._inject_permissions = True` in `get()`.
   - Never set flag on list/paginated views, POST, or PATCH — GET detail only.
3. **Tests**: Test `_permissions` presence in GET, absence in PATCH/POST/list responses, and correct boolean values per role.

### Frontend Integration Checklist
1. **Types**: Add a `<Resource>Permissions` type in the relevant types file, compose with `WithPermissions<T>` from `@/types/api`.
2. **API**: Update `fetch<Resource>Api` return type to the `WithPerms` composed type. Update test mock data.
3. **UI**: Use `<Can allowed={permissions.can_x}>` component (`@/components/common/Can`) to gate elements.

## Explore / Search Integration (adding a new searchable entity)
- Reference implementation: `apps/explore/` (backend), `features/explore/` (frontend)
- Existing entities: **Business** (public, 11 filters) and **User** (auth-required, 5 filters)

### Backend Checklist
1. **Selector**: Add `ExploreSelector.search_<entity>()` in `apps/explore/selectors.py`.
   - FTS: `SearchVector` (weighted A/B/C) + `SearchQuery(q, search_type="websearch")` for relevance.
   - Trigram: `TrigramSimilarity` on name fields as typo-tolerant fallback (scaled `* 0.5`).
   - Combined: `Greatest(fts_rank, trigram_rank)`, filter `search_rank > 0.01`.
   - Filters: exact match, `__in` (CSV lists), `__contains` with OR reduce (tags/JSON arrays), range (`__gte`/`__lte`), bool.
   - Ordering: `relevance` (default), `name`, `newest`.
2. **Serializer**: Slim output serializer in `apps/explore/serializers.py` — only public-facing fields.
3. **View**: `APIView` + `StandardPagination` in `apps/explore/views.py`. Use `_extract_<entity>_params()` helper.
   - Parse CSV → `_parse_csv()`, bools → `_parse_bool()`, ints → `_parse_int()`.
4. **URL**: Add path in `apps/explore/urls.py`.
5. **Tests**: View tests mock `ExploreSelector` (SQLite-safe). Selector tests need `requires_postgres` marker.

### Frontend Checklist
1. **Types**: Add `Explore<Entity>`, `Explore<Entity>Profile`, `<Entity>SearchParams` in `types/explore.ts`.
2. **API**: Add `search<Entity>Api()` in `features/explore/api/explore-api.ts`.
3. **Query key**: Add to `queryKeys.explore` in `lib/query-keys.ts`.
4. **Hook**: Add `useInfinite<Entity>Search()` in `features/explore/hooks/use-explore-queries.ts` — uses `useInfiniteQuery` + `getNextPage()` helper.
5. **Content component**: Infinite scroll pattern — `useInView` from `react-intersection-observer` triggers `fetchNextPage()`.
6. **Card component**: Display card for search results.
7. **Filters component**: Horizontal flex-wrap inside `rounded-lg border bg-muted/40 p-4`.
   - Reuse: `CountrySelect`, `CityCombobox` (static `cities.json`), `TagInput` (autocomplete from `/explore/tags/`).
   - Enum values MUST match backend `TextChoices` exactly (e.g., `CompanySize`, `BusinessType`).
8. **FilterPanel**: Add active-filter detection for the indicator badge.
9. **ExplorePage**: Add tab, read URL params in `useMemo`, wire filter `onChange` → `updateUrl`.

## Skills Mandates
- IMPORTANT: Use `project-documentation` skill for all feature documentation and progress tracking.
- IMPORTANT: Use `configuring-project-memory` skill when modifying CLAUDE.md or project memory.
- IMPORTANT: Use `skill-creator-pro` skill when creating or improving Claude skills.
- IMPORTANT: Use `ilinxa-frontend-standards` skill for all frontend code (React, Next.js, React Native).
