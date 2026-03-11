# API Integration Tests — Execution Guide

## Quick Start

```bash
# Terminal 1: Start Docker infrastructure
make dev-up

# Terminal 2: Run migrations + start Django server
make dev-migrate && make dev

# Terminal 3: Run all API integration tests
make test-api
```

## Prerequisites

### 1. Docker Services Running

```bash
# Verify both services are healthy
docker ps
# Expected: dev_postgres (healthy), dev_redis (healthy)
```

| Service | Container | Port | Health Check |
|---------|-----------|------|-------------|
| PostgreSQL 17 | `dev_postgres` | 5432 | `pg_isready` |
| Redis 7 | `dev_redis` | 6379 | `redis-cli ping` |

### 2. Database Migrated

```bash
make dev-migrate
# Seeds: 51 RBAC permissions, 3 system forms, 1 platform account
```

### 3. Django Server Running

```bash
make dev
# Runs on http://localhost:8000 with local_docker settings
# PostgreSQL for DB, Redis for cache
```

### 4. Rate Limits Relaxed for Testing

The `local_docker` settings override DRF throttle rates to prevent rate limiting during test execution:

| Throttle Scope | Production | Test (local_docker) |
|---------------|-----------|-------------------|
| `login` | 5/minute | 100/minute |
| `password_reset` | 3/hour | 100/hour |
| `anon` | 100/hour | 1000/hour |
| `user` | 1000/hour | 10000/hour |

No Celery worker is needed — tests use `DBHelper` to retrieve verification codes and password reset tokens directly from PostgreSQL.

## Running Tests

### Full Suite

```bash
make test-api
# Equivalent to:
# cd backend && python -m pytest tests/api_integration/ -v --tb=short -x
```

The `-x` flag stops on first failure. Remove it to run all tests:

```bash
cd backend && python -m pytest tests/api_integration/ -v --tb=short
```

### Single Phase

```bash
# Run only auth tests
cd backend && python -m pytest tests/api_integration/test_phase_01_auth.py -v

# Run only CMS tests
cd backend && python -m pytest tests/api_integration/test_phase_08_cms.py -v
```

### Single Test Class

```bash
cd backend && python -m pytest tests/api_integration/test_phase_01_auth.py::TestAuthRegister -v
```

### Single Test

```bash
cd backend && python -m pytest tests/api_integration/test_phase_01_auth.py::TestAuthRegister::test_a01_register_alice -v
```

### With Extra Verbosity

```bash
cd backend && python -m pytest tests/api_integration/ -v --tb=long -s
# -s: show print statements
# --tb=long: full tracebacks
```

## Test Execution Order

Tests MUST run in alphabetical file order (pytest default). State flows forward:

```
Phase 01 (Auth)           → Registers 4 users, establishes tokens
    ↓
Phase 02 (Users)          → Profile CRUD, avatar, memberships
    ↓
Phase 03 (Platform)       → Configure platform, Alice becomes owner
    ↓
Phase 04 (Business+RBAC)  → Create businesses, roles, member management
    ↓
Phase 05 (RBAC Platform)  → Platform roles, 51 permissions verified
    ↓
Phase 06 (Transactions)   → Invitations, requests, lifecycle actions
    ↓
Phase 07 (Forms)          → Template CRUD, response lifecycle
    ↓
Phase 08 (CMS)            → Sites, pages, templates, media, API keys
    ↓
Phase 09 (Notifications)  → Preferences, history, SES webhooks
    ↓
Phase 10 (Cross-Domain)   → 7 end-to-end workflows (independent users)
    ↓
Phase 11 (Negative)       → Error handling, validation, rate limiting
    ↓
Phase 12 (Infrastructure) → PostgreSQL JSONB/FK/unique, Redis cache/JTI
```

**Important**: Phases 1-9 share state (session-scoped fixtures). Phase 10 creates
fresh users per workflow. Phases 11-12 reuse state from earlier phases.

## Resetting Test Data

To start fresh (deletes all data):

```bash
make test-api-reset
# Equivalent to: make dev-down dev-up dev-migrate
```

This stops containers, removes volumes, restarts, and re-runs migrations.

## Test Users

| Name | Email | Password | Purpose |
|------|-------|----------|---------|
| Alice | `alice@test.com` | `TestPass123!` | Platform owner, business owner, full access |
| Bob | `bob@test.com` | `TestPass123!` | Business member, limited access |
| Carol | `carol@test.com` | `TestPass123!` | Business member, used for deny/dismiss |
| Nobody | `nobody@test.com` | `TestPass123!` | No memberships, permission rejection tests |

Cross-domain workflows (Phase 10) create additional users with random email suffixes.

## Troubleshooting

### "Django server not running"
```bash
# Tests auto-skip if server is down
make dev  # Start server in separate terminal
```

### "PostgreSQL not available"
```bash
make dev-up  # Start Docker containers
docker ps    # Verify dev_postgres is healthy
```

### "Redis not available"
```bash
make dev-up          # Start Docker containers
docker exec -it dev_redis redis-cli ping  # Should return PONG
```

### "No verification code found"
```bash
# Tests use DBHelper.get_verification_code() to read codes directly from PostgreSQL
# If this fails, check that migrations have run: make dev-migrate
# Verify the user was registered: check Django server logs for 201 on /auth/register/
```

### Tests Fail With 500 Errors
```bash
# Check Django server logs in the terminal running `make dev`
# Common causes:
# - Missing migrations: make dev-migrate
# - Missing seed data: check migration output for errors
```

### "Duplicate key" or State Conflicts
```bash
# Reset the database for a clean run
make test-api-reset
```

### Permission Denied (403) Unexpected
```bash
# Verify platform is configured (Phase 03 must complete first)
# Verify RBAC permissions are seeded (51 expected)
# Check: curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/rbac/permissions/
```

## Architecture

### Why `requests` Library (Not DRF APIClient)

- Tests the **full HTTP stack**: WSGI server, all middleware, URL routing
- **Realistic**: same as a real client (browser, mobile app)
- **No Django test DB**: no rollback/truncation complications
- **State persists**: data created in Phase 01 is available in Phase 12
- **Infrastructure included**: tests real PostgreSQL and Redis behavior

### Session-Scoped Fixtures

```python
api        # APIHelper — HTTP client with token management
state      # TestState — shared state across all phases
db         # DBHelper — direct PostgreSQL queries
redis_helper  # RedisHelper — direct Redis queries
```

### DBHelper for Out-of-Band Data

Some data (email verification codes, password reset tokens) is only sent via email.
DBHelper queries PostgreSQL directly to retrieve this data:

```python
code = db.get_verification_code("alice@test.com")   # 6-digit code
token = db.get_password_reset_token("alice@test.com")  # UUID
db.verify_user_directly("alice@test.com")  # Bypass email flow
resp_id = db.create_system_form_response(user_id, "system-business-verification", {...})  # System form
```

### X-Client-Type: mobile

All tests send `X-Client-Type: mobile` header, which makes the server return
refresh tokens in the response body (instead of HttpOnly cookies). This is
essential for test automation since we can't read cookies set with HttpOnly.

## File Reference

| File | Tests | Lines | What |
|------|-------|-------|------|
| `conftest.py` | — | ~634 | APIHelper, TestState, DBHelper (incl. system form responses), RedisHelper |
| `test_phase_01_auth.py` | 31 | ~380 | Register, login, refresh, logout, verify, password, sessions, OAuth |
| `test_phase_02_users.py` | 11 | ~180 | /me/, profile, avatar, memberships, deactivate |
| `test_phase_03_platform.py` | 10 | ~200 | Configure, profile, settings, access control |
| `test_phase_04_business_rbac.py` | 32 | ~450 | Business CRUD, lifecycle, roles, members |
| `test_phase_05_rbac_platform.py` | 15 | ~250 | Permissions, platform roles, platform members |
| `test_phase_06_transactions.py` | 19 | ~380 | Invitations, requests, lifecycle, forms (T15 uses DBHelper for system form) |
| `test_phase_07_forms.py` | 18 | ~300 | Templates, fields, responses, lifecycle |
| `test_phase_08_cms.py` | 42 | ~500 | Sites, pages, templates, content, media, API keys, public |
| `test_phase_09_notifications.py` | 11 | ~150 | Preferences, history, types, SES webhooks |
| `test_phase_10_cross_domain.py` | 7 | ~450 | 7 end-to-end workflows |
| `test_phase_11_negative.py` | 41 | ~400 | Auth, authz, validation, conflicts, 404s, rate limiting |
| `test_phase_12_infrastructure.py` | 39 | ~300 | PG JSONB/FK/unique/isolation, Redis cache/JTI/rate/Celery |
| **Total** | **276** | **~4,802** | **275 passed, 1 skipped (A27)** |

## Known Skips

| Test | Reason | Resolution |
|------|--------|-----------|
| A27 (`test_a27_revoke_session`) | Requires 2+ concurrent sessions — test creates only 1 login session, so there's no "other" session to revoke | Future: login from 2 different sessions, then revoke one |

## Production Bugs Discovered by Integration Tests

The test suite uncovered **5 production bugs** that were invisible to unit tests (SQLite + monkey-patches):

| Bug | File | Root Cause | Impact |
|-----|------|-----------|--------|
| 1. `SELECT FOR UPDATE` + nullable FK | `auth_service.py` | `select_for_update()` with `select_related('session')` — nullable FK causes LEFT OUTER JOIN, which PostgreSQL rejects | Token refresh broken on PostgreSQL |
| 2. UUID not JSON-serializable | `auth_service.py` | `user.id` (UUID) passed directly to JWT encoder | Access token creation failed |
| 3. `@transaction.atomic` rollback | `auth_service.py` | `logout_all()` rolled back when `TokenInvalid` raised inside same atomic block | Logout changes lost on refresh error |
| 4. Email retry count not persisted | `tasks.py` | Missing `log.save()` after incrementing `retry_count` | Retry count never updated |
| 5. Wrong AuditLog enum name | `preference_service.py` | `PREFERENCE_UPDATED` doesn't exist — correct is `NOTIFICATION_PREFERENCE_UPDATED`. Unit tests masked this with a monkey-patch. | Notification preference updates returned 500 |

## Application Gaps Closed

| Gap | Description | Fix |
|-----|------------|-----|
| Duplicate membership invitations | `TransactionService.create_invitation()` didn't check if target user already had an active membership | Added `MembershipSelector.get_active_membership_for_user_account()` check → returns 409 |
