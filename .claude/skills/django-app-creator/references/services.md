# Services

Read this when implementing write operations — create/update/delete, transactions, business rules, audit trails, observability, and the AuditContext pattern.

## Quick Reference — Project Imports

```python
from typing import Optional
from dataclasses import dataclass
from django.db import transaction
from django.http import HttpRequest

from apps.core.observability import get_logger, AuditService, AuditLog
from apps.core.exceptions import NotFound, ConflictError, ValidationError
from apps.products.models import Product
from apps.products.selectors import ProductSelector

logger = get_logger(__name__)
```

---

## 1. Role of Services

Services are the **ONLY place that mutates data**. They orchestrate how domain objects change.

Services SHOULD: perform all writes (create/update/delete), enforce business rules & workflows, manage transactions, coordinate multiple models, emit logs and audit events.

Services SHOULD NOT: contain domain meaning (models), perform complex reads (selectors), depend on HTTP objects, hide side effects.

> **Services answer "what should happen?"**

---

## 2. Structure (Full Observability Pattern)

```python
class ProductService:
    @staticmethod
    @transaction.atomic
    def create_product(
        *,
        name: str,
        price: Decimal,
        owner: User,
        request: Optional[HttpRequest] = None
    ) -> Product:
        """Create product with full audit trail."""
        if ProductSelector.exists_by_name(name=name):
            raise ConflictError(
                message="Product with this name already exists",
                resource="Product",
                conflict_type="duplicate"
            )

        product = Product.objects.create(name=name, price=price, owner=owner)

        logger.info("product.created", product_id=str(product.id), name=name, owner_id=str(owner.id))

        AuditService.log(
            action=AuditLog.Action.PRODUCT_CREATED,
            actor=owner,
            resource=product,
            request=request,
        )

        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        *,
        product: Product,
        name: Optional[str] = None,
        price: Optional[Decimal] = None,
        updated_by: User,
        request: Optional[HttpRequest] = None
    ) -> Product:
        """Update product with change tracking."""
        changes = {}

        if name is not None and product.name != name:
            if ProductSelector.exists_by_name(name=name):
                raise ConflictError(message="Product with this name already exists", resource="Product", conflict_type="duplicate")
            changes['name'] = {'old': product.name, 'new': name}
            product.name = name

        if price is not None and product.price != price:
            changes['price'] = {'old': str(product.price), 'new': str(price)}
            product.price = price

        if changes:
            product.save(update_fields=list(changes.keys()) + ['updated_at'])
            logger.info("product.updated", product_id=str(product.id), fields=list(changes.keys()))
            AuditService.log(action=AuditLog.Action.PRODUCT_UPDATED, actor=updated_by, resource=product, request=request, changes=changes)

        return product

    @staticmethod
    @transaction.atomic
    def soft_delete_product(
        *,
        product: Product,
        deleted_by: User,
        request: Optional[HttpRequest] = None
    ) -> Product:
        """Soft delete product."""
        product.soft_delete(user=deleted_by)
        logger.info("product.deleted", product_id=str(product.id))
        AuditService.log(action=AuditLog.Action.PRODUCT_DELETED, actor=deleted_by, resource=product, request=request)

        transaction.on_commit(lambda: cleanup_product_task.delay(product.id))
        return product
```

---

## 3. Adding New Audit Actions

When creating a new domain, add actions to `apps/core/observability/audit/models.py`:

```python
class Action(models.TextChoices):
    PRODUCT_CREATED = "product.created", "Product Created"
    PRODUCT_UPDATED = "product.updated", "Product Updated"
    PRODUCT_DELETED = "product.deleted", "Product Deleted"
```

---

## 4. AuditContext DTO (Recommended Improvement)

Instead of passing `HttpRequest` into services (which couples domain to web framework), use a lightweight DTO:

```python
@dataclass
class AuditContext:
    actor_id: int
    ip_address: str | None = None
    user_agent: str | None = None

    @classmethod
    def from_request(cls, request: HttpRequest) -> "AuditContext":
        return cls(
            actor_id=request.user.id,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
        )
```

Usage: views create `AuditContext`, services accept it. Services never depend on `HttpRequest`.

---

## 5. Method Design Rules

- **Keyword-only arguments** (MANDATORY)
- **`@transaction.atomic`** on all write methods
- **Static methods** (services are stateless)
- **Use `get_logger(__name__)`** for structured logging
- **Use `AuditService.log()`** for audit trails on sensitive operations
- **Use `transaction.on_commit()`** for async tasks after DB commit
- **Raise domain exceptions** (`ConflictError`, `ValidationError`, `NotFound`)

---

## 6. Validation Split

| Layer | Validates |
|-------|-----------|
| Serializer | Input format, required fields |
| Service | Business rules, uniqueness |
| Model | Structural constraints |

---

## 7. Read / Write Separation

Services MAY read data but MUST NOT implement reusable read logic. Reusable reads belong in selectors.

Allowed: `Product.objects.filter(email__iexact=email).exists()`
Preferred: `ProductSelector.exists_by_email(email=email)`

---

## 8. Side Effects & I/O

- Logging and auditing: allowed inside services
- File & network I/O: MUST NOT occur inside DB locks
- Use `transaction.on_commit()` for post-save actions

---

## 9. Error Handling

- Raise domain-specific exceptions (never swallow silently)
- Let the API layer map exceptions to HTTP responses
- Use structured data in exceptions: `ConflictError(resource="Product", conflict_type="duplicate")`

---

## 10. Idempotency & Concurrency

When needed: concurrent operations, external side effects (emails, APIs).

Tools: `select_for_update()`, status fields, retry-on-conflict logic.

Simple CRUD usually does NOT need idempotency.

---

## 11. Anti-Patterns

❌ `print(f"Created product {id}")` — Use `logger.info()` with structured data
❌ No audit trail for sensitive operations
❌ `from django.core.exceptions import ValidationError` — Use `apps.core.exceptions`
❌ `from rest_framework.exceptions import NotFound` — Use `apps.core.exceptions`
❌ Serializers in services
❌ QuerySet `.update()` (use instance `.save()` for audit tracking)
❌ Silent errors
❌ HTTP request objects deep in domain layer (use AuditContext)
