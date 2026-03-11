# Selectors

Read this when writing read queries — single-entity retrieval, list queries, eager loading, existence checks, and error handling for missing resources.

## Quick Reference — Project Imports

```python
from django.db.models import QuerySet, Q, F, Subquery, Count, Prefetch
from apps.core.exceptions import NotFound
from apps.products.models import Product
```

---

## 1. Role of Selectors

Selectors represent **read-only access to the domain**. Zero side effects.

Selectors SHOULD: contain all reusable read queries, apply query optimization, return QuerySets or domain objects, provide consistent error behavior.

Selectors SHOULD NOT: write to the database, perform side effects, contain business workflows, depend on HTTP objects.

> **Selectors answer "what exists?"**

---

## 2. Structure

```python
class ProductSelector:
    @staticmethod
    def get_by_id(*, product_id: int) -> Product:
        """Get product by ID, raise NotFound if missing or deleted."""
        product = Product.objects.filter(id=product_id).first()
        if not product:
            raise NotFound(resource="Product", resource_id=product_id)
        return product

    @staticmethod
    def get_by_id_or_none(*, product_id: int) -> Product | None:
        """Get product by ID, return None if missing."""
        return Product.objects.filter(id=product_id).first()

    @staticmethod
    def get_by_id_including_deleted(*, product_id: int) -> Product:
        """Get product including soft-deleted (for recovery/admin)."""
        product = Product.all_objects.filter(id=product_id).first()
        if not product:
            raise NotFound(resource="Product", resource_id=product_id)
        return product

    @staticmethod
    def list_by_owner(*, owner_id: int, with_details: bool = False) -> QuerySet[Product]:
        """Return QuerySet — caller handles pagination."""
        qs = Product.objects.filter(owner_id=owner_id)
        if with_details:
            qs = qs.select_related('owner').prefetch_related('categories')
        return qs

    @staticmethod
    def exists_by_name(*, name: str) -> bool:
        """Fast existence check for uniqueness validation."""
        return Product.objects.filter(name__iexact=name).exists()
```

---

## 3. Method Design Rules

- **Keyword-only arguments** (MANDATORY)
- **Static methods** (selectors are stateless)
- **Dual variants**: `get_by_x()` raises `NotFound`, `get_by_x_or_none()` returns `None`
- **Return QuerySets** for lists (not materialized lists) — pagination is the caller's responsibility
- **Use `.exists()`** for boolean checks (not `count() > 0`)
- **Use `NotFound` from `apps.core.exceptions`** — never leak `DoesNotExist`
- **Use `all_objects`** only when explicitly including deleted records

---

## 4. Query Construction

Avoid `Model.objects.all()` in production selectors. Prefer filtered queries.

### Reusable base helper (recommended)

```python
@staticmethod
def _qs(*, with_profile: bool = False):
    qs = User.objects
    return qs.with_profile() if with_profile else qs
```

---

## 5. Eager Loading

- `select_related()` for ForeignKey / OneToOne
- `prefetch_related()` for ManyToMany / reverse relations
- Expose eager-loading intent explicitly: `with_details=True`
- Use `with_<relation>()` naming on QuerySets

> Selectors are the **only layer responsible** for query optimization.

---

## 6. Scope & Safety

- Multi-tenant / soft-delete scoping applied at selector level — never rely on callers
- Large QuerySets: callers MUST apply pagination or limits
- Aggregations: use `annotate()`, `Count()`, `Subquery()`, document added fields

---

## 7. Anti-Patterns

❌ `except Product.DoesNotExist: raise` — Convert to `NotFound(resource="Product", ...)`
❌ `raise Exception("Product not found")` — Use `NotFound` with resource info
❌ Writing to database
❌ Side effects (logging, auditing)
❌ Business rules
❌ HTTP request objects
