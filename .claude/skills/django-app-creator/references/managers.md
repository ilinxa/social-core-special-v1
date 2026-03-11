# Managers & QuerySets

Read this when creating custom managers, QuerySets, creation methods, or extending SoftDeleteManager for BaseModel subclasses.

## Quick Reference — Project Imports

```python
from django.db import models
from apps.core.models import BaseModel
from apps.core.models.managers import SoftDeleteManager
```

---

## 1. Role & Boundaries

Managers SHOULD: define creation rules (defaults, normalization), provide safe constructors (`create_*`), attach custom QuerySets.

Managers SHOULD NOT: orchestrate workflows, trigger side effects (emails, tasks), implement domain meaning, encode HTTP/serializer concerns.

> **Managers create objects. Models describe objects. Services execute use-cases.**

---

## 2. BaseModel Already Has SoftDeleteManager

When using `BaseModel` or any soft-delete model, managers are already attached:
- `objects` = SoftDeleteManager (excludes `is_deleted=True`)
- `all_objects` = models.Manager (includes all records)

---

## 3. Custom QuerySets

QuerySets provide **chainable read helpers**:

```python
class ProductQuerySet(models.QuerySet):
    def in_stock(self):
        return self.filter(quantity__gt=0)

    def by_category(self, category):
        return self.filter(category=category)

    def with_owner(self):
        """Eager-load owner to prevent N+1"""
        return self.select_related('owner')
```

Rules: return QuerySets (never lists), no writes, name by intent (`active()`, `with_profile()`).

### Eager-loading naming
- `select_related()` for ForeignKey / OneToOne
- `prefetch_related()` for ManyToMany / reverse relations
- Use `with_<relation>()` naming for eager-loading helpers

---

## 4. Extending SoftDeleteManager

When extending a BaseModel's manager, **inherit from SoftDeleteManager**:

```python
class ProductManager(SoftDeleteManager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def create_product(self, *, name, price, owner, **extra):
        """Creation with normalization and defaults"""
        name = name.strip()
        return self.create(name=name, price=price, owner=owner, **extra)

class Product(BaseModel):
    objects = ProductManager()
    all_objects = models.Manager()
```

### For Non-SoftDelete Models

```python
class UserManager(models.Manager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def create_user(self, *, email, username, password=None, **extra):
        email = email.lower().strip()
        user = self.model(email=email, username=username, **extra)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
```

---

## 5. Attaching QuerySet to Manager

### Option A (preferred): `as_manager()`
```python
EntityManager = EntityQuerySet.as_manager
```

### Option B: explicit delegation
```python
class EntityManager(models.Manager):
    def get_queryset(self):
        return EntityQuerySet(self.model, using=self._db)
```

---

## 6. Uniqueness & Collision Safety

Generation-time uniqueness checks are not sufficient under concurrency.

Rule: keep DB uniqueness constraints, handle collisions by retrying on `IntegrityError`.

> DB constraints are the real guarantee.

---

## 7. Randomness & Security

Use `secrets` (not `random`) for: usernames, tokens, referral codes.
Keep generated identifiers URL-safe and stable in shape.

---

## 8. Circular Imports

- Prefer `self.model` inside manager methods
- Avoid importing the model at module-level
- If required, import locally inside a method

---

## 9. Testing

- QuerySets: ensure chainable, verify eager-loading reduces queries (`assertNumQueries`)
- Managers: `create_user` hashes password, `create_superuser` enforces flags, unique fields satisfy DB constraints

---

## 10. Anti-Patterns

❌ `objects = models.Manager()` on BaseModel subclass — Loses soft delete filtering
❌ Business workflows in managers
❌ Side effects (emails/tasks)
❌ Authorization rules
❌ Serializer validation
