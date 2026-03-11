# Models

Read this when creating or modifying Django models — field design, base model choice, soft delete, constraints, indexing, domain properties, and migration safety.

## Quick Reference — Project Imports

```python
from apps.core.models import (
    BaseModel,           # TimeStamped + SoftDelete (RECOMMENDED DEFAULT)
    TimeStampedModel,    # created_at, updated_at only
    SoftDeleteModel,     # is_deleted, soft_delete(), restore()
    UserStampedModel,    # created_by, updated_by (extends TimeStamped)
    UUIDModel,           # UUID primary key
    AuditModel,          # UserStamped + SoftDelete (for compliance)
)
from django.db import models
from django.conf import settings  # For AUTH_USER_MODEL
```

---

## 1. Role of Models

Models represent **domain entities**. They define data structure, enforce invariants, and expose meaning.

Models SHOULD: define fields & relations, enforce DB constraints, expose read-only domain properties, be framework-agnostic.

Models SHOULD NOT: orchestrate workflows, send emails/trigger side effects, contain query logic, depend on request/user/session.

> **Models answer "what is true?" — not "what should happen?"**

---

## 2. Base Model Hierarchy

| Need | Model | Provides |
|------|-------|----------|
| Most domain models | `BaseModel` | created_at, updated_at, is_deleted, soft_delete(), restore() |
| Compliance/audit | `AuditModel` | Above + created_by, updated_by |
| UUID primary key | `UUIDModel` | UUID pk (compose with others) |
| Only timestamps | `TimeStampedModel` | created_at, updated_at |
| Only soft delete | `SoftDeleteModel` | is_deleted, deleted_at, deleted_by |

### Structure

```python
from apps.core.models import BaseModel
from django.conf import settings

class Product(BaseModel):
    """BaseModel provides: timestamps, soft delete, objects/all_objects managers."""
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products"
    )

    @property
    def is_affordable(self):
        return self.price < 100

    class Meta:
        db_table = "products"
        verbose_name = "product"
        verbose_name_plural = "products"
        indexes = [models.Index(fields=["owner", "is_deleted"])]
```

### Composing Base Models

```python
from apps.core.models import UUIDModel, BaseModel

class Order(UUIDModel, BaseModel):
    """UUID PK + timestamps + soft delete"""
    total = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        db_table = "orders"

from apps.core.models import AuditModel

class Contract(AuditModel):
    """Timestamps + soft delete + created_by/updated_by"""
    title = models.CharField(max_length=255)
    class Meta:
        db_table = "contracts"
```

---

## 3. Soft Delete Usage

```python
products = Product.objects.all()         # Excludes is_deleted=True
all_products = Product.all_objects.all() # Includes deleted

product.soft_delete(user=request.user)   # Soft delete
product.restore()                        # Restore
```

---

## 4. Database Table Naming

Always define `db_table` explicitly:
```python
class Meta:
    db_table = "products"
```

Why: clean SQL, predictable schema, safer migrations, easier integration.

---

## 5. Human-Readable Names

```python
class Meta:
    verbose_name = "product"
    verbose_name_plural = "products"
```

Affects admin UI, forms, permissions. Never affects database schema.

---

## 6. Field Rules

- `CharField`/`TextField`: use `blank=True`, avoid `null=True`
- `ForeignKey`: `null=True` only if optional, always define `related_name`
- Always use `settings.AUTH_USER_MODEL` for user FKs
- Prefer explicit defaults over nullable fields

---

## 7. Indexing Strategy

### Meta-level indexes (preferred — query-pattern-driven)

```python
class Meta:
    indexes = [
        models.Index(fields=["email", "is_active"]),
        models.Index(fields=["owner", "is_deleted"]),
    ]
```

Rules: index queries not fields, composite order matters (left-most rule), boolean fields alone are not selective enough.

`unique=True` already creates an index.

---

## 8. Constraints (DB-Level Invariants)

Use for impossible states that must never exist:

```python
models.CheckConstraint(
    check=~models.Q(id=models.F("referred_by_id")),
    name="no_self_referral",
)
```

Use for: self-relation prevention, mutual exclusivity, cross-field invariants.
Do NOT use for: workflow rules, permissions, temporary business logic.

> If a rule may change → enforce it in services, not DB.

---

## 9. Relationships

- `ForeignKey`: always define `related_name`, assume indexed by default
- `OneToOneField`: use `primary_key=True` when lifecycle is identical

```python
user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
```

---

## 10. Domain Properties

Express business meaning, not actions:

```python
@property
def is_complete(self):
    return self.is_verified and hasattr(self, "profile")
```

Rules: no side effects, no `.save()` calls, prefer `@property` for state-like logic.

---

## 11. Migration Safety

- Never rename `db_table` casually
- Never remove constraints without data audit
- Avoid dropping indexes blindly
- Treat migrations as irreversible history

---

## 12. Anti-Patterns

❌ `class Product(models.Model)` — Use `BaseModel` instead
❌ `from django.contrib.auth.models import User` — Use `settings.AUTH_USER_MODEL`
❌ `user = models.ForeignKey(User, ...)` — Use `settings.AUTH_USER_MODEL`
❌ HTTP/request logic in models
❌ Sending emails from models
❌ External API calls in models
❌ Business workflows in models
❌ `.delete()` instead of `.soft_delete()` for BaseModel subclasses
❌ Signals that auto-create domain objects (use explicit service calls)
