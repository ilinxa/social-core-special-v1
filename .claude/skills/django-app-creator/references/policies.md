# Policies

Read this when implementing domain authorization — eligibility rules, `can_<action>` methods, the boundary between policies and permissions.

## Quick Reference — Project Imports

```python
from apps.core.exceptions import PermissionDenied, ConflictError
```

---

## 1. Role of Policies

Policies answer one question: **"Is this action allowed under current domain rules?"**

They are independent from HTTP, serializers, views, services execution details, and side effects.

Policies SHOULD: decide authorization & eligibility, express business permission rules, be pure and deterministic, fail loudly.

Policies MUST NOT: write to the database, send emails/notifications, call external services, trigger tasks, depend on request/session objects.

> **If a policy has side effects, it is no longer a policy.**

---

## 2. Structure

```python
class ProductPolicy:
    @staticmethod
    def can_update(*, actor: User, product: Product) -> None:
        if product.owner_id != actor.id and not actor.is_staff:
            raise PermissionDenied(
                message="Cannot update another user's product",
                action="update",
                resource="Product"
            )

    @staticmethod
    def can_delete(*, actor: User, product: Product) -> None:
        if product.owner_id != actor.id and not actor.is_staff:
            raise PermissionDenied(
                message="Cannot delete another user's product",
                action="delete",
                resource="Product"
            )

    @staticmethod
    def can_transfer(*, actor: User, product: Product, new_owner: User) -> None:
        if product.owner_id != actor.id:
            raise PermissionDenied(message="Only owner can transfer", action="transfer", resource="Product")
        if new_owner.id == actor.id:
            raise PermissionDenied(message="Cannot transfer to yourself", action="transfer", resource="Product")
```

---

## 3. Method Design Rules

- **Static, stateless methods**
- **Keyword-only arguments** (MANDATORY)
- **Raise exceptions**, not return booleans — prevents ignored results
- **Include action and resource** in exception for audit context
- File: `{entity}_policy.py`, Class: `{Entity}Policy`, Methods: `can_<action>`

---

## 4. Where Policies Are Called

Called from: **Commands** (preferred) or **Services** (acceptable when commands are skipped).

Never called from: models, serializers, signals, tasks, templates.

---

## 5. Read Access Rules

Policies MAY read from passed domain objects and perform lightweight checks.
Policies SHOULD NOT perform reusable queries — fetch via selector first, pass results into policy.

---

## 6. Policies vs Permissions

| Concern | Permissions (API) | Policies (Domain) |
|---------|------------------|-------------------|
| Layer | HTTP/delivery | Domain |
| Scope | Coarse (authenticated?) | Fine-grained (can do X?) |
| Context | Request-based | Domain-based |
| Business rules | ❌ | ✅ |
| Import from | `apps.core.permissions` | `apps.core.exceptions` |

> Permissions decide **who may enter**. Policies decide **what they may do**.

---

## 7. Testing

Test policies with pure unit tests — no database writes, minimal fixtures. Focus on: allowed cases, forbidden cases, edge states. No mocks needed (prefer real domain objects).

---

## 8. Anti-Patterns

❌ `return False` instead of raising — Always raise exceptions
❌ `from rest_framework.exceptions import PermissionDenied` — Use `apps.core.exceptions`
❌ Writing to DB in policies
❌ Checking `request.user` inside policy
❌ Combining policy + workflow
❌ Silent permission failures
