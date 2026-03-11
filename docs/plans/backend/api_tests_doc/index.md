# API Integration Test Plan — Index

## Purpose

This test plan provides a comprehensive blueprint for testing all backend API endpoints against the real Docker infrastructure stack (PostgreSQL 17 + Redis 7). The goal is to verify that every endpoint, cross-domain workflow, and infrastructure-dependent feature works correctly before building new features on top of the existing codebase.

**What unit tests already cover (2591 tests, SQLite + DummyCache):**
- Model validation, constraints, and business logic
- Service layer operations with mocked dependencies
- Selector queries (basic SQL)
- Policy enforcement (permission checks)
- Serializer validation
- View request/response shapes

**What API integration tests will additionally verify:**
- Full HTTP request/response cycle through all middleware layers
- PostgreSQL-specific behavior (JSONB, UUID FK integrity, unique constraints with soft-delete)
- Real Redis (permission caching, JTI blacklist, rate limiting)
- Cross-domain workflows spanning 2-3 systems
- Auth flow end-to-end with real JWT tokens
- Error response format consistency across all endpoints

## Prerequisites

### 1. Docker Infrastructure

```bash
# Start PostgreSQL 17 + Redis 7
make dev-up

# Verify services are healthy
docker ps  # Both dev_postgres and dev_redis should be "healthy"
```

**Services:**
| Service | Container | Port | Image |
|---------|-----------|------|-------|
| PostgreSQL | `dev_postgres` | 5432 | `postgres:17-alpine` |
| Redis | `dev_redis` | 6379 | `redis:7-alpine` |

### 2. Database Setup

```bash
# Run all migrations (creates tables + seeds data)
make dev-migrate

# Create superuser for bootstrap operations
cd backend && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker python manage.py createsuperuser
```

### 3. Settings Module

All API tests must use `backend_core.settings.local_docker` which configures:
- **Database**: PostgreSQL (`backend_core_db` on `localhost:5432`)
- **Cache**: Redis (`redis://localhost:6379/1`, prefix `dev`, 300s TTL)
- **Channels**: Redis channel layer (`localhost:6379`)
- **Sessions**: Cache-backed (Redis)
- **CORS**: Allow all origins (development)

### 4. Django Server

```bash
# Start the development server
make dev
# or manually:
cd backend && DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker python manage.py runserver
```

Base URL: `http://localhost:8000/api/v1/`

## Data Seeded by Migrations

After `make dev-migrate`, the database contains:

| Migration | Data | Count |
|-----------|------|-------|
| `organization.0002` | Platform singleton account | 1 |
| `rbac.0002` | Core permissions (membership, roles, settings, platform, audit, forms) | 26 |
| `rbac.0003` | Transaction permissions | 2 |
| `rbac.0004` | CMS permissions (structural, content, media) | 23 |
| `forms.0003` | System forms (business-verification, business-creation, staff-application) | 3 |
| **Total** | | **51 permissions, 3 system forms, 1 platform account** |

## Test User Strategy

### Tier 1: Superuser (via manage.py)

```bash
# Create once during setup
python manage.py createsuperuser --email admin@test.com
```

Used for: bootstrap operations, platform configuration, initial member invitations.

### Tier 2: API-Created Users (via POST /api/v1/auth/register/)

| User | Email | Role | Purpose |
|------|-------|------|---------|
| Alice | `alice@test.com` | Platform owner / Business owner | Full access, creates resources |
| Bob | `bob@test.com` | Platform member / Business member | Limited access, tests permissions |
| Carol | `carol@test.com` | Business member | Tests role-based access |
| Nobody | `nobody@test.com` | No memberships | Tests non-member rejection |

Password for all API users: `TestPass123!`

## Authentication Helper Patterns

### Register + Login

```
POST /api/v1/auth/register/
Content-Type: application/json

{
    "email": "alice@test.com",
    "password": "TestPass123!"
}
# Response: 201 Created
# Returns: { "user": {...}, "tokens": {"access_token": "...", "refresh_token": "..."}, "is_new_user": true }
# Web clients: refresh_token in HttpOnly cookie
# Mobile clients (X-Client-Type: mobile): refresh_token in response body
```

### Login (Get Tokens)

```
POST /api/v1/auth/login/
Content-Type: application/json

{
    "email": "alice@test.com",
    "password": "TestPass123!"
}
# Response: 200 OK
# {
#     "access_token": "eyJ...",
#     "user": { "id": "uuid", "email": "...", ... }
# }
# Also sets: refresh cookie (HttpOnly), has_session cookie
```

### Authenticated Requests

```
GET /api/v1/users/me/
Authorization: Bearer eyJ...access_token...
```

### Token Refresh

```
POST /api/v1/auth/refresh/
Cookie: refresh_token=eyJ...
# Response: 200 OK with new access_token
# Old refresh token is invalidated (single-use rotation)
```

## Error Response Format

All errors follow a consistent format defined in `apps/core/exceptions/handler.py`:

```json
{
    "error": {
        "message": "Human-readable error description",
        "code": "error_type_code",
        "details": {
            "field_name": ["Validation error message"]
        }
    }
}
```

### Status Code Mapping

| Error Code | HTTP Status | When |
|------------|-------------|------|
| `domain_error` | 400 | Business logic violation |
| `validation_error` | 400 | Request data validation failure |
| `business_rule_violation` | 400 | Domain-specific business rule broken |
| `authentication_error` | 401 | Generic auth failure |
| `invalid_credentials` | 401 | Wrong email/password |
| `token_expired` | 401 | JWT access token expired |
| `token_invalid` | 401 | Malformed or tampered token |
| `token_already_used` | 401 | Refresh token reuse detected |
| `account_not_verified` | 401 | Email not yet verified |
| `account_inactive` | 401 | Deactivated account |
| `permission_denied` | 403 | Authenticated but lacks permission |
| `not_found` | 404 | Resource does not exist |
| `conflict` | 409 | Duplicate or state conflict |
| `rate_limit_exceeded` | 429 | Too many requests |
| `service_unavailable` | 503 | External service down |

## URL Routing Overview

All endpoints are prefixed with `/api/v1/`. The 13 domain groups:

| Domain | URL Prefix | URL Paths | HTTP Operations |
|--------|------------|-----------|-----------------|
| Auth | `/auth/` | 17 | 17 |
| Users | `/users/` | 5 | 9 |
| Platform | `/platform/` (org) | 3 | 5 |
| Business | `/business/` (org) | 9 | 13 |
| RBAC Platform | `/platform/` (roles/members) | 10 | 14 |
| RBAC Business | `/business/<slug>/` (roles/members) | 10 | 14 |
| RBAC Shared | `/rbac/` | 1 | 1 |
| Transaction | `/transactions/` | 12 | 13 |
| Forms | `/forms/` | 13 | 17 |
| CMS Admin | `/cms/admin/` | 17 | 27 |
| CMS Public | `/cms/public/` | 2 | 2 |
| Notifications | `/notifications/` | 4 | 6 |
| Email | `/email/` | 1 | 1 |
| **Total** | | **104** | **~139** |

## Test Plan Document

The full test plan with all scenarios is in:

**[api_integration_test_plan.md](./api_integration_test_plan.md)**

Organized as:
- **Part 1** — Setup & Prerequisites
- **Part 2** — Domain-Specific Test Scenarios (13 domains, ~165 test cases)
- **Part 3** — Cross-Domain Integration Scenarios (7 workflows, ~80 steps)
- **Part 4** — Negative Testing (~32 test cases)
- **Part 5** — PostgreSQL-Specific Verification (~19 test cases)
- **Part 6** — Redis-Specific Verification (~14 test cases)

## Useful Commands

```bash
# Start infrastructure
make dev-up

# Run migrations
make dev-migrate

# Start Django server
make dev

# PostgreSQL shell
make dev-dbshell

# Redis CLI
make dev-redis-cli

# Stop infrastructure
make dev-down

# Reset all data (deletes volumes)
docker compose -f docker-compose.dev.yml down -v
```
