# Permissions

Read this when configuring API-level authorization — DRF permission classes, core permission imports, object-level permissions, and the IsOwner field configuration.

## Quick Reference — Project Imports

```python
from apps.core.permissions import (
    # Authentication
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    # Staff/Admin
    IsStaff,
    IsStaffOrReadOnly,
    IsSuperuser,
    # Ownership
    IsOwner,                   # obj.owner == request.user (configurable field)
    IsOwnerOrStaff,
    IsOwnerOrReadOnly,
    # Verification
    IsVerified,                # User.is_verified == True
    # Utility
    AllowAny,
    DenyAll,
)
```

**Always import from `apps.core.permissions`**, not `rest_framework.permissions`.

---

## 1. Role of Permissions

Permissions are **delivery-layer guards** at the HTTP/API boundary.

Permissions answer: **"May this request access this endpoint?"**

Permissions SHOULD: check authentication state, check coarse authorization (role, ownership), be fast and side-effect free, be reusable across views.

Permissions MUST NOT: write to the database, perform business workflows, enforce complex domain rules, replace policies, depend on serializers.

> **Permissions guard entry; Policies guard intent; Services guard correctness.**

---

## 2. Permission Reference

| Permission | Use When |
|------------|----------|
| `IsAuthenticated` | Default for most endpoints |
| `IsAuthenticatedOrReadOnly` | Public read, authenticated write |
| `IsOwner` | User can only access their own resources |
| `IsOwnerOrStaff` | Owner or admin can access |
| `IsVerified` | Email verification required |
| `IsStaff` | Admin-only endpoints |
| `IsSuperuser` | Superuser-only endpoints |
| `AllowAny` | Public endpoints (registration, login) |
| `DenyAll` | Temporarily disabled features |

---

## 3. Usage in Views

```python
class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request, product_id):
        product = ProductSelector.get_by_id(product_id=product_id)
        self.check_object_permissions(request, product)
        ...

class PublicProductListView(APIView):
    permission_classes = [AllowAny]

class PremiumFeatureView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]
```

---

## 4. Configuring IsOwner Field

`IsOwner` checks `obj.owner` by default. For models using different field names:

```python
class IsPostAuthor(IsOwner):
    owner_field = 'author'  # Check obj.author instead of obj.owner
```

---

## 5. Object-Level Permissions

Use carefully and only when:
- The object is already loaded
- The rule is trivial (ownership, membership)

Avoid: complex state checks, multi-object reasoning, workflow-dependent logic. Those belong in **policies**.

---

## 6. Permissions vs Policies

| Concern | Permissions (API) | Policies (Domain) |
|---------|------------------|-------------------|
| Layer | HTTP/delivery | Domain |
| Scope | Coarse (authenticated?) | Fine-grained (can do X?) |
| Context | Request-based | Domain-based |
| Business rules | ❌ | ✅ |
| Import from | `apps.core.permissions` | `apps.core.exceptions` |

Both may coexist for the same action.

---

## 7. Testing

Test with API tests (preferred) and minimal unit tests. Focus on: allowed vs denied access, authenticated vs unauthenticated, role-based access.

---

## 8. Rules

- **Always import from `apps.core.permissions`**
- **Declare `permission_classes` explicitly** on every view
- **Fast checks only** (no heavy queries)
- **No database writes**
- **No business rules** (use policies for domain logic)

---

## 9. Anti-Patterns

❌ `from rest_framework.permissions import IsAuthenticated` — Use `apps.core.permissions`
❌ Undeclared `permission_classes` (defaults vary, be explicit)
❌ Heavy database queries in permissions
❌ Business logic in permissions (use policies instead)
❌ Calling services from permissions
❌ Depending on serializers
