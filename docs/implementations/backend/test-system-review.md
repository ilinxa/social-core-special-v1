# Test System — Comprehensive Review

**Last Updated:** 2026-02-22
**Status:** Review complete
**Coverage Run:** 489 passed, 3 skipped, 0 failed | 76% overall coverage

---

## 1. Executive Summary

The test system is well-structured with strong conventions. Three apps (users, organization, rbac) have thorough test coverage across all layers (models, services, selectors, views). However, **4 apps have zero tests** (auth, core, email, notifications), which drags overall coverage to 76% — below the project's 80% minimum requirement.

### Strengths
- Consistent pytest + factory-boy patterns across all tested apps
- Deep RBAC testing (66 actor-scenario integration tests)
- Full layer coverage where tests exist (models → selectors → services → views)
- Well-structured conftest hierarchy (global → app-specific)
- Audit trail verification via mock patching

### Gaps
- 4 out of 7 apps have **no tests at all**
- No serializer-specific test files (serializers tested indirectly via view tests)
- No async/WebSocket/Celery task tests
- No `.coveragerc` file — no exclusion rules for admin, migrations, etc.
- `showlocals` in pytest.ini triggers a warning (deprecated config location)

---

## 2. Test Infrastructure

### 2.1 Configuration

| File | Purpose |
|------|---------|
| [pytest.ini](backend/pytest.ini) | Test runner config (settings, markers, CLI options) |
| [tests/conftest.py](backend/tests/conftest.py) | Global fixtures (API clients, users, utilities) |
| [tests/factories.py](backend/tests/factories.py) | Global factories (UserFactory, AdminFactory) |
| [tests/TESTING_INSTRUCTIONS.md](backend/tests/TESTING_INSTRUCTIONS.md) | Testing guidelines and conventions |
| [.claude/skills/django-testing/SKILL.md](.claude/skills/django-testing/SKILL.md) | Claude testing skill with patterns and templates |

### 2.2 pytest.ini Settings

```ini
django_settings_module = backend_core.settings.local    # SQLite for speed
markers: slow, integration, unit, e2e                   # 4 registered markers
addopts = -v --tb=short --strict-markers -ra            # verbose, short tracebacks
norecursedirs = migrations, venv, staticfiles, ...      # skip non-test dirs
minversion = 7.0
```

**Issue:** `showlocals = true` in pytest.ini produces `PytestConfigWarning: Unknown config option: showlocals` — this should be `--showlocals` in `addopts` instead.

### 2.3 Registered Markers

| Marker | Purpose | Actually Used? |
|--------|---------|----------------|
| `@pytest.mark.slow` | Deselect slow tests with `-m "not slow"` | No |
| `@pytest.mark.integration` | Integration tests | No |
| `@pytest.mark.unit` | Unit tests | No |
| `@pytest.mark.e2e` | End-to-end tests | No |
| `@pytest.mark.django_db` | Database access (from pytest-django) | Yes, everywhere |

None of the custom markers (slow, integration, unit, e2e) are actually used in any test file. Tests only use `@pytest.mark.django_db`.

### 2.4 Makefile Targets

| Command | What It Does |
|---------|--------------|
| `make test` | `pytest -v` (SQLite, default settings) |
| `make test-cov` | `pytest --cov=. --cov-report=term-missing --cov-report=html` |
| `make test-fast` | `pytest -x -q` (stop on first failure, quiet) |
| `make test-watch` | `ptw -- -v` (watch mode, requires pytest-watch) |
| `make test-docker` | `DJANGO_SETTINGS_MODULE=local_docker pytest -v` (PostgreSQL + Redis) |
| `make check` | `make lint && make test` (lint + test gate) |

---

## 3. Coverage Analysis (Real Numbers)

### 3.1 Overall

```
Total statements: 10,374
Missed:           2,511
Coverage:         76%        ← BELOW 80% MINIMUM
```

### 3.2 Coverage By App

| App | Stmts | Miss | Cover | Test Files | Status |
|-----|-------|------|-------|------------|--------|
| **users** | 810 | 66 | **92%** | 4 (models, selectors, services, views) | Excellent |
| **rbac** | 1,122 | 79 | **93%** | 6 (models, policies, selectors, services, views, actor_scenarios) | Excellent |
| **organization** | 958 | 108 | **89%** | 6 (business: models/services/views, platform: models/services/views) | Good |
| **core** | 956 | 327 | **66%** | 0 test files | No tests |
| **auth** | 1,269 | 951 | **25%** | 0 test files | No tests |
| **email** | 539 | 463 | **14%** | 0 test files | No tests |
| **notifications** | 579 | 406 | **30%** | 0 test files | No tests |

### 3.3 Worst Coverage Files (0% — completely untested)

| File | Stmts | What It Does |
|------|-------|-------------|
| `auth/blacklist.py` | 78 | Token blacklisting (refresh token revocation) |
| `auth/consumers.py` | 66 | WebSocket authentication consumers |
| `auth/middleware.py` | 34 | JWT authentication middleware |
| `auth/selectors.py` | 44 | Auth query helpers (sessions, tokens) |
| `auth/tasks.py` | 34 | Celery tasks (token cleanup, session expiry) |
| `core/middleware/__init__.py` | 1 | Middleware init |
| `core/observability/admin.py` | 32 | Audit log admin interface |
| `core/observability/audit/constants.py` | 4 | Audit action constants |
| `core/observability/audit/decorators.py` | 23 | Audit decorators |
| `core/observability/logging/celery.py` | 22 | Celery logging integration |
| `core/observability/metrics/*` | 54 | Metrics interface, noop, validation |
| `email/selectors.py` | 50 | Email query helpers |
| `email/services/backends/*` | 116 | Email backends (console, SES, SMTP) |
| `email/services/email_service.py` | 109 | Core email sending service |
| `email/tasks.py` | 58 | Celery email tasks |
| `notifications/services/channels/*` | 75 | Notification channels (email, push, SMS) |
| `notifications/services/notification_service.py` | 77 | Core notification dispatch |
| `notifications/services/preference_service.py` | 69 | Notification preferences |
| `notifications/tasks.py` | 86 | Celery notification tasks |
| `rbac/permissions/registry.py` | 15 | Permission registry |

### 3.4 Coverage by Layer (tested apps only)

| Layer | users | organization | rbac |
|-------|-------|-------------|------|
| Models | 97% | 99% | 100% |
| Managers | 97% | — | — |
| Selectors | 91% | 65-80% | 97% |
| Services | 100% | 81-93% | 96% |
| Views | 100% | 93-97% | 80% |
| Serializers | 84% | 100% | 100% |
| Policies | — | 79% | 98% |

---

## 4. Test Inventory

### 4.1 Test Count by App

| App | Test Files | Test Classes | Test Methods | Lines of Test Code |
|-----|-----------|-------------|-------------|-------------------|
| **users** | 4 | 30 | 166 | ~920 |
| **rbac** | 6 | 49 | 220 | ~2,780 |
| **organization** | 6 | 22 | 100 | ~500 |
| **auth** | 0 | 0 | 0 | 0 |
| **core** | 0 | 0 | 0 | 0 |
| **email** | 0 | 0 | 0 | 0 |
| **notifications** | 0 | 0 | 0 | 0 |
| **TOTAL** | **16** | **101** | **~486** | **~4,200** |

Note: pytest collects 492 items (some parametrized tests expand).

### 4.2 Test Types Present

| Type | Present? | Example |
|------|----------|---------|
| Unit tests (models) | Yes | `test_models.py` in users, rbac, organization |
| Unit tests (services) | Yes | `test_services.py` in all 3 tested apps |
| Unit tests (selectors) | Yes | `test_selectors.py` in users, rbac |
| API/View tests | Yes | `test_views.py` in all 3 tested apps |
| Policy/Permission tests | Yes | `test_policies.py` in rbac |
| Integration tests | Yes | `test_actor_scenarios.py` (66 tests, 2180 lines) |
| Serializer tests | Indirect | Tested through view tests, no dedicated files |
| WebSocket tests | No | — |
| Celery task tests | No | — |
| Email service tests | No | — |
| Notification tests | No | — |
| Performance/load tests | No | — |
| Migration tests | No | — |

### 4.3 Test File Details

#### Users App (4 files, 166 tests)

| File | Classes | Tests | What It Covers |
|------|---------|-------|---------------|
| `test_models.py` | 6 | 43 | User/Profile creation, constraints, managers, querysets, properties |
| `test_selectors.py` | 7 | 38 | get_by_id/email/username, existence checks, referral queries |
| `test_services.py` | 11 | 45 | Create user, verify email, update profile/avatar, change username/email, deactivate |
| `test_views.py` | 9 | 44 | GET/PATCH/DELETE /me/, profile CRUD, avatar upload/delete, permissions |

#### RBAC App (6 files, 220 tests)

| File | Classes | Tests | What It Covers |
|------|---------|-------|---------------|
| `test_models.py` | 8 | 25 | Permission, Role, RolePermission, Membership models + constraints + managers |
| `test_policies.py` | 8 | 24 | MembershipPolicy authorization, owner invincibility, dominance rule, target checks, role assignment |
| `test_selectors.py` | 3 | 30 | Permission/Role/Membership queries, caching, cache invalidation |
| `test_services.py` | 14 | 43 | Build actor context, initialize accounts, CRUD membership/role/permission, cache invalidation |
| `test_views.py` | 17 | 32 | Business/Platform role/member API endpoints, permission views, error handling |
| `test_actor_scenarios.py` | 16 | 66 | Owner/Admin/Member/PlatformAdmin/GlobalModerator scenarios, cross-account, audit trails, edge cases |

#### Organization App (6 files, 100 tests)

| File | Classes | Tests | What It Covers |
|------|---------|-------|---------------|
| `business/test_models.py` | 3 | 25 | BusinessAccount, BusinessProfile, BusinessSlugHistory models |
| `business/test_services.py` | 2 | 17 | Business CRUD, slug management, suspend/reactivate/archive, profile updates |
| `business/test_views.py` | 8 | 24 | Business list/create/detail/update, slug change, suspend/reactivate/archive API |
| `platform/test_models.py` | 2 | 11 | PlatformAccount singleton, PlatformProfile |
| `platform/test_services.py` | 2 | 11 | Platform configuration, settings merge, profile updates |
| `platform/test_views.py` | 3 | 12 | Platform account/profile/settings API endpoints |

---

## 5. Factory System

### 5.1 Factory Files

| File | Factories | Models Covered |
|------|-----------|---------------|
| [tests/factories.py](backend/tests/factories.py) | 2 | User (basic), Admin |
| [users/tests/factories.py](backend/apps/users/tests/factories.py) | 8 | User (5 variants), UserProfile (3 variants) |
| [rbac/tests/factories.py](backend/apps/rbac/tests/factories.py) | 20 | User, BusinessAccount, PlatformAccount, Permission (3), Role (5), RolePermission (3), Membership (6), BusinessWithOwner |
| [organization/tests/factories.py](backend/apps/organization/tests/factories.py) | 13 | User (3), PlatformAccount, PlatformProfile, BusinessAccount (4), BusinessProfile, BusinessSlugHistory |
| **Total** | **43** | — |

### 5.2 Factory Duplication Issue

`UserFactory` is defined **4 separate times** — once in each factories.py file. Each has slightly different fields and behaviors:

| Location | Username Pattern | is_verified | Creates Profile? |
|----------|-----------------|-------------|------------------|
| `tests/factories.py` | `user0, user1...` | Not set | No |
| `users/tests/factories.py` | `user_00000000...` | `False` | Yes (post-generation) |
| `rbac/tests/factories.py` | `rbac_user_00000000...` | `True` | No |
| `organization/tests/factories.py` | `user0, user1...` | Not set | No |

This is intentional (each app needs slightly different defaults) but creates maintenance overhead. Consider a shared base factory that app-specific factories inherit from.

### 5.3 Notable Factory Patterns

- **`django_get_or_create`** on PlatformAccountFactory (singleton pattern)
- **`skip_postgeneration_save`** on all UserFactories (optimization)
- **`BusinessWithOwnerFactory`** — composite factory that creates a full business setup (account + owner role + base member role + owner membership) in one call
- **`create_profile` post-generation** in users' UserFactory handles the `transaction.on_commit()` issue where signals don't fire during tests

---

## 6. Fixture System

### 6.1 Fixture Hierarchy

```
backend/tests/conftest.py (Global)
├── api_client, authenticated_client, admin_client
├── user, admin_user
├── db_no_rollback
├── json_content_type, sample_image
└── settings_debug_true, settings_debug_false

backend/apps/users/tests/conftest.py
├── 5 API client variants (api, authenticated, verified, staff, admin)
├── 7 user fixtures (user, verified, staff, superuser, inactive, referred, another)
├── 6 factory fixtures (return factory class for dynamic creation)
├── 1 composite fixture (user_with_complete_profile)
├── 4 file upload fixtures (sample_image, jpeg, oversized, invalid)
└── 3 URL fixtures (me_url, profile_url, avatar_url)

backend/apps/rbac/tests/conftest.py
├── 2 skip markers (skip_if_sqlite, skip_if_locmem_cache)
├── 2 API client fixtures
├── 3 user fixtures
├── 3 account fixtures (business, another_business, platform)
├── 13 permission fixtures (generic + 8 named permissions)
├── 8 role fixtures (business + platform variants)
├── 6 membership fixtures
├── 2 composite fixtures (business_with_members, role_with_permissions)
└── 6 URL fixtures

backend/apps/organization/tests/conftest.py
├── 4 API client fixtures
├── 4 user fixtures
├── 5 platform fixtures
├── 7 business fixtures
└── 3 factory fixtures
```

### 6.2 Fixture Statistics

| Conftest | Fixture Count | Lines |
|----------|---------------|-------|
| Global | 9 | 175 |
| Users | 25 | 272 |
| RBAC | 50+ | 594 |
| Organization | 23 | 222 |
| **Total** | **~107** | **~1,263** |

### 6.3 Fixture Issues

- **Overlapping fixtures**: `api_client`, `authenticated_client`, `admin_client` are defined in BOTH global conftest AND each app's conftest. App-level fixtures shadow global ones.
- **No fixture scoping**: All fixtures use default `scope="function"` — no `scope="session"` or `scope="class"` for expensive fixtures like PlatformAccount.
- **Missing conftest**: `auth`, `core`, `email`, `notifications` apps have `tests/__init__.py` but no `conftest.py` or `factories.py`.

---

## 7. Mocking & Patching

### 7.1 What Gets Mocked

| Target | Where Used | Why |
|--------|-----------|-----|
| `apps.users.services.AuditService.log` | users/test_services.py | Verify audit trail calls without DB writes |
| `apps.rbac.services.AuditService.log` | rbac/test_actor_scenarios.py | Verify audit trail for 11 action types |
| `cache.clear()` | rbac tests | Reset cache before building actor context |

### 7.2 What Does NOT Get Mocked

- Database operations (per project standards)
- Django signals
- File uploads (uses real SimpleUploadedFile)
- Serializer validation

### 7.3 Missing Mocking

- **No external service mocking**: Google/Apple OAuth backends, AWS SES, SMTP — these would need mocking for auth/email tests
- **No Celery task mocking**: Tasks are `ALWAYS_EAGER` in test settings so they run synchronously, but there are no tests for them

---

## 8. Test Patterns & Conventions

### 8.1 Standard Test Structure

```
apps/{app}/tests/
├── __init__.py
├── conftest.py         # App-specific fixtures
├── factories.py        # Factory-boy factories
├── test_models.py      # Model creation, constraints, managers, querysets
├── test_selectors.py   # Query helper tests
├── test_services.py    # Business logic tests
├── test_views.py       # API endpoint tests
├── test_policies.py    # Authorization policy tests (rbac only)
└── test_actor_scenarios.py  # Integration tests (rbac only)
```

### 8.2 Conventions Followed

- All tests use `@pytest.mark.django_db` (never Django TestCase)
- Test classes group related tests (no inheritance, purely organizational)
- AAA pattern (Arrange-Act-Assert) throughout
- Descriptive method names: `test_create_user_with_duplicate_email_raises_conflict`
- Factory-boy for all test data (no manual `Model.objects.create()`)
- API tests use DRF's `APIClient` via fixtures
- Audit logging verified with `@patch` + `mock.assert_called_once_with()`

### 8.3 Conditional Skip Decorators

| Decorator | Where Defined | Purpose |
|-----------|---------------|---------|
| `@skip_if_sqlite` | rbac conftest | Skips tests using PostgreSQL-specific JSONField lookups |
| `@skip_if_locmem_cache` | rbac conftest | Skips cache invalidation tests that need Redis |

These are only used in RBAC tests (3 skipped tests on SQLite/DummyCache).

---

## 9. Missing Coverage — Detailed Gap Analysis

### 9.1 Auth App (0% tested, ~1,270 statements)

| Component | Stmts | Critical? | What Needs Testing |
|-----------|-------|-----------|-------------------|
| `services/auth_service.py` | 195 | **HIGH** | Login, logout, token refresh, session management |
| `views.py` | 248 | **HIGH** | 14+ API endpoints (login, register, refresh, logout, password reset, verify email, OAuth) |
| `services/password_service.py` | 88 | HIGH | Password reset flow, change password |
| `services/verification_service.py` | 76 | HIGH | Email verification tokens |
| `services/oauth_service.py` | 92 | MEDIUM | Google/Apple OAuth flows (requires mocking) |
| `authentication.py` | 44 | MEDIUM | JWT authentication backend |
| `backends/google.py` | 72 | MEDIUM | Google OAuth backend |
| `backends/apple.py` | 89 | MEDIUM | Apple OAuth backend |
| `blacklist.py` | 78 | MEDIUM | Token blacklisting/revocation |
| `consumers.py` | 66 | LOW | WebSocket auth (requires channel testing) |
| `middleware.py` | 34 | LOW | JWT middleware |
| `tasks.py` | 34 | LOW | Celery cleanup tasks |
| `selectors.py` | 44 | LOW | Query helpers |

### 9.2 Core App (66% coverage, but no dedicated tests)

Coverage comes from being exercised by other apps' tests. Missing:

| Component | Stmts | Miss | What Needs Testing |
|-----------|-------|------|-------------------|
| `observability/admin.py` | 32 | 32 | Audit log admin views |
| `observability/audit/decorators.py` | 23 | 18 | `@audit_action` decorator |
| `observability/audit/selectors.py` | 48 | 29 | Audit log queries |
| `observability/logging/celery.py` | 22 | 22 | Celery logging integration |
| `observability/metrics/*` | 54 | 54 | Metrics system (noop, interface, validation) |
| `utils/datetime.py` | 59 | 36 | Date utility functions |
| `utils/jwt.py` | 34 | 22 | JWT encode/decode utilities |
| `utils/password.py` | 36 | 21 | Password validation utilities |
| `permissions/base.py` | 64 | 26 | Custom permission classes |

### 9.3 Email App (14% coverage, 0 tests)

| Component | Stmts | What Needs Testing |
|-----------|-------|--------------------|
| `services/email_service.py` | 109 | Email composition, template rendering, sending |
| `services/backends/` | 116 | Console, SES, SMTP backends |
| `services/sns_verifier.py` | 54 | SNS signature verification |
| `services/template_renderer.py` | 30 | HTML template rendering |
| `webhooks.py` | 99 | AWS SNS webhook handling (bounce, complaint, delivery) |
| `selectors.py` | 50 | Email log queries |
| `tasks.py` | 58 | Async email sending tasks |

### 9.4 Notifications App (30% coverage, 0 tests)

| Component | Stmts | What Needs Testing |
|-----------|-------|--------------------|
| `services/notification_service.py` | 77 | Multi-channel dispatch |
| `services/preference_service.py` | 69 | User preference management |
| `services/channels/` | 75 | Email, push, SMS channel implementations |
| `selectors.py` | 61 | Notification queries, unread counts |
| `tasks.py` | 86 | Async notification dispatch |
| `views.py` | 51 | Notification list/read/preferences API |

---

## 10. Configuration Issues

| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| `showlocals = true` produces warning | pytest.ini | Minor (cosmetic warning every run) | Move to `addopts = --showlocals` |
| No `.coveragerc` | Missing | Coverage includes migrations, admin, __init__ — inflates miss count | Create `.coveragerc` with `omit` rules |
| Custom markers never used | pytest.ini | Dead configuration | Either use them or remove to avoid confusion |
| Overall coverage 76% | — | Below 80% mandate | Add tests for auth, email, notifications, core |
| Duplicate UserFactory x4 | 4 factories.py files | Maintenance overhead | Consider shared base factory |
| Overlapping conftest fixtures | Global + app-level | Shadowing (works but confusing) | Remove duplicates from global or document intentional shadowing |

---

## 11. Recommendations

### P0 — Must Fix (to meet 80% coverage mandate)

1. **Add auth app tests** — Login, register, token refresh, logout, password reset are critical paths. Mock external OAuth providers.
2. **Add core utility tests** — `utils/jwt.py`, `utils/password.py`, `utils/datetime.py` are used everywhere. Pure functions, easy to test.
3. **Create `.coveragerc`** — Exclude migrations, admin, `__init__.py`, test files from coverage calculation.

### P1 — Should Fix

4. **Add email app tests** — Mock SMTP/SES backends, test template rendering, test SNS webhook verification.
5. **Add notification app tests** — Test `NotificationService.send()` dispatch, preference management, channel selection.
6. **Fix `showlocals` config warning** — Move from ini option to `addopts`.
7. **Add serializer test files** — Currently only tested indirectly through views. Dedicated `test_serializers.py` would catch validation edge cases.

### P2 — Nice to Have

8. **Use registered markers** — Annotate tests with `@pytest.mark.unit`, `@pytest.mark.integration` for selective runs.
9. **Add fixture scoping** — `scope="session"` for PlatformAccount singleton, expensive setup.
10. **Consolidate UserFactory** — Create a shared base in `tests/factories.py` that app-level factories extend.
11. **Add WebSocket tests** — Test auth consumers using Django Channels test utilities.
12. **Add Celery task tests** — Test task functions directly (they run sync in test mode).

---

## 12. File Summary

### Test Infrastructure Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/pytest.ini` | 47 | Test runner configuration |
| `backend/tests/conftest.py` | 175 | Global fixtures |
| `backend/tests/factories.py` | ~50 | Global factories |
| `backend/tests/TESTING_INSTRUCTIONS.md` | ~200 | Testing guidelines |
| `apps/users/tests/conftest.py` | 272 | Users fixtures |
| `apps/users/tests/factories.py` | ~65 | Users factories |
| `apps/rbac/tests/conftest.py` | 594 | RBAC fixtures (largest) |
| `apps/rbac/tests/factories.py` | ~124 | RBAC factories |
| `apps/organization/tests/conftest.py` | 222 | Organization fixtures |
| `apps/organization/tests/factories.py` | ~81 | Organization factories |

### Test Files

| File | Lines | Tests |
|------|-------|-------|
| `users/tests/test_models.py` | 224 | 43 |
| `users/tests/test_selectors.py` | 208 | 38 |
| `users/tests/test_services.py` | 271 | 45 |
| `users/tests/test_views.py` | 215 | 44 |
| `rbac/tests/test_models.py` | 154 | 25 |
| `rbac/tests/test_policies.py` | 190 | 24 |
| `rbac/tests/test_selectors.py` | 189 | 30 |
| `rbac/tests/test_services.py` | 316 | 43 |
| `rbac/tests/test_views.py` | 300 | 32 |
| `rbac/tests/test_actor_scenarios.py` | 626 | 66 |
| `organization/tests/business/test_models.py` | 87 | 25 |
| `organization/tests/business/test_services.py` | 97 | 17 |
| `organization/tests/business/test_views.py` | 112 | 24 |
| `organization/tests/platform/test_models.py` | 57 | 11 |
| `organization/tests/platform/test_services.py` | 64 | 11 |
| `organization/tests/platform/test_views.py` | 66 | 12 |

### Empty Test Directories (only `__init__.py`)

| Path | App | Needs |
|------|-----|-------|
| `apps/auth/tests/` | auth | conftest.py, factories.py, test_*.py |
| `apps/core/tests/` | core | conftest.py, test_utils.py, test_permissions.py |
| `apps/email/tests/` | email | conftest.py, factories.py, test_*.py |
| `apps/notifications/tests/` | notifications | conftest.py, factories.py, test_*.py |
