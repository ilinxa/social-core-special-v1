---
name: django-app-creator
description: >
  Create and modify Django apps following layered architecture. Covers models, managers, selectors, services,
  serializers, views, URLs, policies, commands, tasks, signals, permissions. Uses apps.core base models,
  exceptions, permissions, pagination, observability. Triggers when creating apps, models, views, services,
  serializers, selectors, managers, tasks, policies, permissions, pagination, APIs, endpoints, or modifying
  app structure. Never put business logic in views, serializers, or models.
---

# Django App Creation & Architecture

**All Django apps live in `apps/` directory.**

## Quick Start — Core Infrastructure Imports

```python
# Models — ALWAYS inherit from core base models
from apps.core.models import BaseModel  # TimeStamped + SoftDelete (recommended default)
from django.db import models
from django.conf import settings  # For AUTH_USER_MODEL

# Exceptions — NEVER use Django/DRF exceptions directly
from apps.core.exceptions import NotFound, ValidationError, ConflictError, PermissionDenied

# Observability — MANDATORY for services/views/tasks
from apps.core.observability import get_logger, AuditService, AuditLog
from apps.core.observability.logging.celery import LoggedTask

# Serializers — Use base classes
from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer

# Permissions — Use core permissions
from apps.core.permissions import IsAuthenticated, IsOwner, AllowAny

# Pagination — Use core pagination
from apps.core.pagination import StandardPagination, CursorResultsPagination

# Services
from django.db import transaction

# Selectors
from django.db.models import QuerySet

# Views
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
```

---

## Architecture Flow

```
HTTP REQUEST → urls.py (routing only)
    → views.py (HTTP orchestration)
        ├→ INPUT SERIALIZERS (validation)
        ├→ SELECTORS (read-only queries)
        └→ SERVICES (writes, business rules, transactions)
            → MANAGERS (construction & normalization)
                → MODELS (meaning & invariants)
                    → DATABASE
    ← OUTPUT SERIALIZERS (response shaping) ← HTTP RESPONSE

After commit → SIGNALS → async tasks / logging / cache invalidation
```

---

## Task Router

| Task | Read |
|------|------|
| Creating/modifying models, base model choice, soft delete, constraints | [references/models.md](references/models.md) |
| Custom managers, QuerySets, creation methods, SoftDeleteManager | [references/managers.md](references/managers.md) |
| Read queries, optimization, eager loading, existence checks | [references/selectors.md](references/selectors.md) |
| Write operations, transactions, audit trails, business rules | [references/services.md](references/services.md) |
| Input/output serializers, validation, BaseInputSerializer | [references/serializers.md](references/serializers.md) |
| API views, HTTP orchestration, OpenAPI docs, AuditContext | [references/views.md](references/views.md) |
| URL routing, namespaces, versioning, me/ endpoints | [references/urls.md](references/urls.md) |
| Domain authorization, eligibility rules, can_<action> | [references/policies.md](references/policies.md) |
| Intent expression, use-case boundary, commands layer | [references/commands.md](references/commands.md) |
| Async tasks, Celery, retries, idempotency, LoggedTask | [references/tasks.md](references/tasks.md) |
| Event reactions, signal handlers, delegation | [references/signals.md](references/signals.md) |
| API-level guards, DRF permissions, core permission classes | [references/permissions.md](references/permissions.md) |

---

## Universal Rules

- **Keyword-only arguments** in all services, selectors, policies, commands: `def method(*, arg: type)`
- **`@transaction.atomic`** on all service methods that write to DB
- **`settings.AUTH_USER_MODEL`** for all user ForeignKeys (never `User` directly)
- **Separate input/output serializers** — never reuse for both directions
- **`is_valid(raise_exception=True)`** on all input serializers in views
- **`extend_schema()`** on all view methods — summary, request, responses, tags
- **`base=LoggedTask`** on all Celery tasks for correlation_id tracing
- **`transaction.on_commit()`** for scheduling async tasks from services

---

## Model Hierarchy

| Need | Model | Provides |
|------|-------|----------|
| Most domain models | `BaseModel` | created_at, updated_at, soft delete |
| Compliance/audit tracking | `AuditModel` | Above + created_by, updated_by |
| UUID primary key | `UUIDModel` | UUID pk (compose with others) |
| Only timestamps | `TimeStampedModel` | created_at, updated_at only |
| Only soft delete | `SoftDeleteModel` | is_deleted, soft_delete(), restore() |

All from `apps.core.models`. BaseModel managers: `objects` (excludes deleted), `all_objects` (includes deleted).

---

## Exception Reference

All from `apps.core.exceptions`. Never use Django/DRF exceptions directly.

| Exception | HTTP | Use When |
|-----------|------|----------|
| `NotFound` | 404 | Resource doesn't exist |
| `PermissionDenied` | 403 | User lacks permission |
| `ValidationError` | 400 | Business rule validation fails |
| `ConflictError` | 409 | Duplicate or state conflict |
| `AuthenticationError` | 401 | Auth required or failed |
| `InvalidCredentials` | 401 | Wrong email/password |
| `TokenExpired` | 401 | Token has expired |
| `TokenInvalid` | 401 | Malformed/invalid token |
| `AccountNotVerified` | 401 | Email verification required |
| `AccountInactive` | 401 | User account inactive |
| `BusinessRuleViolation` | 400 | Domain rule violated |
| `RateLimitExceeded` | 429 | Too many attempts |
| `ServiceUnavailable` | 503 | External service down |

---

## Pagination Reference

All from `apps.core.pagination`.

| Class | Items/Page | Use For |
|-------|------------|---------|
| `StandardPagination` | 20 | Default for most endpoints |
| `SmallResultsPagination` | 10 | Dropdowns, autocomplete |
| `LargeResultsPagination` | 50 | Admin listings, exports |
| `LimitOffsetResultsPagination` | 20 | Direct offset control |
| `CursorResultsPagination` | 20 | Large datasets, feeds, timelines |
| `IDCursorPagination` | 20 | Cursor by ID (no timestamps) |
| `NoPagination` | all | Config/enum endpoints |

---

## Top Anti-Patterns

❌ `class Product(models.Model)` → ✅ `class Product(BaseModel)`
❌ `from django.contrib.auth.models import User` → ✅ `settings.AUTH_USER_MODEL`
❌ `from django.core.exceptions import ValidationError` → ✅ `apps.core.exceptions`
❌ `from rest_framework.permissions import IsAuthenticated` → ✅ `apps.core.permissions`
❌ `from rest_framework.exceptions import NotFound` → ✅ `apps.core.exceptions`
❌ `class ProductSerializer(ModelSerializer)` for input → ✅ `BaseInputSerializer`
❌ `print(f"Created {id}")` → ✅ `logger.info("product.created", product_id=str(id))`
❌ `@shared_task` without `base=LoggedTask` → ✅ `@shared_task(base=LoggedTask)`
❌ `product.delete()` → ✅ `product.soft_delete(user=request.user)`
❌ Business logic in views, serializers, or signals
❌ ORM queries in views (use selectors)
❌ `.save()` calls in views (use services)

---

## Architecture Checklist

### Core Infrastructure
- [ ] Models inherit from core base models
- [ ] User FKs use `settings.AUTH_USER_MODEL`
- [ ] Exceptions from `apps.core.exceptions`
- [ ] Permissions from `apps.core.permissions`
- [ ] Pagination from `apps.core.pagination`
- [ ] Serializers inherit `BaseInputSerializer` / `BaseOutputSerializer`

### Observability
- [ ] Services use `get_logger(__name__)`
- [ ] Services use `AuditService.log()` for audit trails
- [ ] Tasks use `base=LoggedTask`

### Layer Responsibilities
- [ ] Models define meaning, not actions
- [ ] Managers normalize inputs, not orchestrate
- [ ] Selectors handle all reads (raise `NotFound`)
- [ ] Services are the ONLY place that writes to DB
- [ ] Serializers validate format, not business rules
- [ ] Views orchestrate, never decide
- [ ] All services/selectors/policies use keyword-only args
- [ ] All writes wrapped in `@transaction.atomic`
- [ ] Tasks scheduled with `transaction.on_commit()`
- [ ] OpenAPI schema on all endpoints

---

## Mental Model

- **Models** define truth · **Managers** construct objects · **Selectors** retrieve data
- **Services** change the system · **Serializers** validate & shape · **Views** orchestrate HTTP
- **Policies** protect actions · **Commands** express intent · **Tasks** schedule work
- **Signals** observe events · **Permissions** guard endpoints

> If it changes state → Service. If it reads data → Selector.
> If it validates format → Serializer. If it checks permission → Policy.

---

## CLAUDE.md Integration

```markdown
- IMPORTANT: Always use django-app-creator skill when creating or modifying Django apps. Use apps.core base models, exceptions, permissions, pagination, and observability. Never put business logic in views, serializers, or models. Always use keyword-only arguments in services, selectors, policies.
```
