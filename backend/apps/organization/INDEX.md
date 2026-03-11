# Organization System Index

**Version:** 1.0.1
**Last Updated:** 2026-02-09
**Status:** Implemented
**Dependencies:** `apps.core` (models, exceptions, observability, serializers, permissions)

---

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Platform Models | `platform/models.py` | Singleton platform account |
| Business Models | `business/models.py` | Multi-tenant business accounts |
| Constants | `apps/core/constants.py` | Shared enums |
| Audit Actions | `apps/core/observability/audit/models.py` | `org.*` actions |

---

## 1. Models

### 1.1 PlatformAccount (Singleton)
```
Location: platform/models.py
Table: platform_account
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `singleton_key` | PositiveSmallInt | Always 1, unique constraint |
| `is_configured` | Boolean | Initial setup complete? |
| `settings` | JSON | Platform-wide settings |

**Constraints:**
- `platform_account_singleton`: CHECK `singleton_key=1`
- Unique on `singleton_key`

**Inheritance:** `AuditModel` (created_at, updated_at, created_by, updated_by, soft delete)

### 1.2 PlatformProfile
```
Location: platform/models.py
Table: platform_profile
```

| Field | Type | Notes |
|-------|------|-------|
| `platform` | OneToOne(PK) | FK to PlatformAccount |
| `name` | CharField(255) | Platform name |
| `tagline` | CharField(500) | Optional |
| `description` | TextField | Optional |
| `logo` | ImageField | `platform/logo/` |
| `favicon` | ImageField | `platform/favicon/` |
| `primary_color` | CharField(7) | Hex, default `#000000` |
| `secondary_color` | CharField(7) | Hex, default `#ffffff` |
| `contact_email` | EmailField | Optional |
| `contact_phone` | CharField(20) | Optional |
| `address` | TextField | Optional |
| `social_links` | JSON | Dict of URLs |

### 1.3 BusinessAccount
```
Location: business/models.py
Table: business_account
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `slug` | SlugField(100) | Unique, indexed |
| `legal_name` | CharField(255) | Required |
| `registration_number` | CharField(100) | Optional |
| `tax_id` | CharField(100) | Optional |
| `country` | CharField(2) | ISO 3166-1 alpha-2 |
| `legal_address` | TextField | Optional |
| `business_type` | CharField(30) | BusinessType enum |
| `status` | CharField(20) | BusinessStatus enum |
| `verification_status` | CharField(20) | VerificationStatus enum |
| `verified_at` | DateTime | Nullable |
| `verified_by` | FK(User) | Nullable |
| `settings` | JSON | Business settings |

**Managers:**
- `objects` = `BusinessAccountManager` (filters `is_deleted=False`)
- `all_objects` = `Manager` (includes deleted)

**Manager Methods:**
- `active()` → status=ACTIVE
- `verified()` → active + verification_status=VERIFIED
- `pending_verification()` → active + verification_status=PENDING

**Inheritance:** `AuditModel`

### 1.4 BusinessProfile
```
Location: business/models.py
Table: business_profile
```

| Field | Type | Notes |
|-------|------|-------|
| `business` | OneToOne(PK) | FK to BusinessAccount |
| `display_name` | CharField(255) | Public name |
| `tagline` | CharField(500) | Optional |
| `description` | TextField | Optional |
| `logo` | ImageField | `business/logos/%Y/%m/` |
| `cover_image` | ImageField | `business/covers/%Y/%m/` |
| `website` | URLField | Optional |
| `contact_email` | EmailField | Optional |
| `contact_phone` | CharField(20) | Optional |
| `industry` | CharField(100) | Optional |
| `company_size` | CharField(20) | CompanySize enum |
| `founded_year` | PositiveInt | Optional |
| `social_links` | JSON | Dict of URLs |
| `custom_fields` | JSON | Form Builder extensions |
| `is_public` | Boolean | Default True |

### 1.5 BusinessSlugHistory
```
Location: business/models.py
Table: business_slug_history
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | BigAutoField | PK |
| `business` | FK | BusinessAccount |
| `old_slug` | SlugField(100) | **Unique globally** |
| `changed_at` | DateTime | Auto |

**Invariant:** Old slugs can NEVER be reused.

---

## 2. Enums (apps/core/constants.py)

| Enum | Values |
|------|--------|
| `AccountType` | PLATFORM, BUSINESS |
| `ContextType` | PLATFORM, BUSINESS, USER |
| `OwnerType` | SYSTEM, PLATFORM, BUSINESS |
| `FormScope` | PLATFORM, BUSINESS |
| `PermissionScope` | BUSINESS, PLATFORM_ONLY, GLOBAL_ONLY, PLATFORM_AND_GLOBAL |
| `MembershipStatus` | ACTIVE, SUSPENDED, LEFT, REMOVED, BANNED |
| `BusinessType` | SOLE_PROPRIETORSHIP, PARTNERSHIP, LLC, CORPORATION, NONPROFIT, COOPERATIVE, OTHER |
| `BusinessStatus` | PENDING, ACTIVE, SUSPENDED, ARCHIVED, DELETED |
| `VerificationStatus` | UNVERIFIED, PENDING, VERIFIED, REJECTED, EXPIRED |
| `CompanySize` | 1, 2-10, 11-50, 51-200, 201-500, 500+ |

---

## 3. Services

### 3.1 PlatformAccountService
```
Location: platform/services.py
```

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `configure()` | name, settings, actor, request | PlatformAccount | One-time setup |
| `update_settings()` | settings, actor, request | PlatformAccount | Merges settings |

### 3.2 PlatformProfileService
```
Location: platform/services.py
```

| Method | Args | Returns |
|--------|------|---------|
| `update()` | name, tagline, ..., actor, request | PlatformProfile |

### 3.3 BusinessAccountService
```
Location: business/services.py
```

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_business()` | owner, legal_name, country, ... | BusinessAccount | owner=request.user |
| `update()` | business, legal_name, ..., actor | BusinessAccount | |
| `update_slug()` | business, new_slug, actor | BusinessAccount | Stores old in history |
| `suspend()` | business, reason, actor | BusinessAccount | Staff only |
| `reactivate()` | business, actor | BusinessAccount | Staff only |
| `archive()` | business, actor | BusinessAccount | Owner only |
| `soft_delete()` | business, actor | BusinessAccount | Owner/superuser |
| `update_verification_status()` | business, status, actor | BusinessAccount | For Transaction system |

### 3.4 BusinessProfileService
```
Location: business/services.py
```

| Method | Args | Returns |
|--------|------|---------|
| `update()` | profile, display_name, ..., actor | BusinessProfile |

---

## 4. Selectors

### 4.1 PlatformAccountSelector
```
Location: platform/selectors.py
```

| Method | Returns | Raises |
|--------|---------|--------|
| `get()` | PlatformAccount | NotFound |
| `exists()` | bool | - |
| `is_configured()` | bool | - |

### 4.2 BusinessAccountSelector
```
Location: business/selectors.py
```

| Method | Returns | Raises |
|--------|---------|--------|
| `get_by_id(business_id)` | BusinessAccount | NotFound |
| `get_by_slug(slug)` | BusinessAccount | NotFound |
| `get_by_slug_or_redirect(slug)` | (BusinessAccount, redirect_slug\|None) | NotFound |
| `list_active()` | QuerySet | - |
| `list_verified()` | QuerySet | - |
| `list_pending_verification()` | QuerySet | - |
| `list_by_country(country)` | QuerySet | - |
| `slug_exists(slug, exclude_id)` | bool | - |
| `list_by_owner(user)` | QuerySet | RBAC stub |
| `list_by_member(user)` | QuerySet | RBAC stub |

---

## 5. API Endpoints

### 5.1 Platform (`/api/v1/platform/`)

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/account/` | GET | Authenticated | Get platform |
| `/account/` | POST | Superuser | Configure (once) |
| `/profile/` | GET | Authenticated | Get profile |
| `/profile/` | PATCH | Staff | Update profile |
| `/settings/` | PATCH | Superuser | Update settings |

### 5.2 Business (`/api/v1/business/`)

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/` | GET | Authenticated | List active |
| `/` | POST | Authenticated | Create (becomes owner) |
| `/my/` | GET | Authenticated | List user's businesses |
| `/id/{uuid}/` | GET | Authenticated | Get by UUID |
| `/{slug}/` | GET | Authenticated | Get by slug (redirects) |
| `/{slug}/` | PATCH | Owner/Staff | Update |
| `/{slug}/` | DELETE | Owner/Superuser | Soft delete |
| `/{slug}/profile/` | GET | Authenticated | Get profile |
| `/{slug}/profile/` | PATCH | Owner/Staff | Update profile |
| `/{slug}/slug/` | PATCH | Owner | Change slug |
| `/{slug}/suspend/` | POST | Staff | Suspend |
| `/{slug}/reactivate/` | POST | Staff | Reactivate |
| `/{slug}/archive/` | POST | Owner | Archive |

---

## 6. Audit Actions

```
Location: apps/core/observability/audit/models.py → AuditLog.Action
```

| Action | When |
|--------|------|
| `org.platform.configured` | Initial platform setup |
| `org.platform.settings_updated` | Settings changed |
| `org.platform.profile_updated` | Profile changed |
| `org.business.created` | Business created |
| `org.business.updated` | Business updated |
| `org.business.suspended` | Business suspended |
| `org.business.reactivated` | Business reactivated |
| `org.business.archived` | Business archived |
| `org.business.deleted` | Business soft deleted |
| `org.business.slug_changed` | Slug changed |
| `org.business.profile_updated` | Profile updated |
| `org.verification.approved` | Verification approved |
| `org.verification.rejected` | Verification rejected |
| `org.ownership.transfer_initiated` | Ownership transfer started |

---

## 7. RBAC Integration Points

**Stubs in `business/services.py`:**
```python
# In create_business():
# RBACService.initialize_business_account(business_id, owner, request)

# In selectors.py list_by_owner/list_by_member:
# Query Membership with is_owner=True or status=ACTIVE
```

**Key rule:** Ownership is tracked via `Membership.is_owner=True`, NOT by role name.

---

## 8. Invariants

| Rule | Enforcement |
|------|-------------|
| Platform singleton | DB: unique + check constraint on `singleton_key=1` |
| Slug uniqueness | DB: unique constraint on `BusinessAccount.slug` |
| No slug reuse | DB: unique constraint on `BusinessSlugHistory.old_slug` |
| Owner on create | Service: `owner=request.user` becomes initial owner |

---

## 9. Code Patterns

### 9.1 Serializers
```python
# Input serializers - inherit from BaseInputSerializer
from apps.core.serializers import BaseInputSerializer

class BusinessCreateInput(BaseInputSerializer):
    legal_name = serializers.CharField(max_length=255)
    # ... no create()/update() methods

# Output serializers - inherit from BaseOutputSerializer
from apps.core.serializers import BaseOutputSerializer

class BusinessAccountOutput(BaseOutputSerializer):
    class Meta:
        model = BusinessAccount
        fields = ["id", "slug", "legal_name", ...]
        read_only_fields = fields
```

### 9.2 Permissions
```python
# Always import from apps.core.permissions, NOT rest_framework.permissions
from apps.core.permissions import IsAuthenticated

class BusinessListCreateView(APIView):
    permission_classes = [IsAuthenticated]
```

### 9.3 Views Pattern
```python
# Always pass context to output serializers
output = BusinessAccountOutput(business, context={'request': request})
return Response(output.data)
```

### 9.4 Policies
```python
# Policies return booleans, views raise PermissionDenied
if not BusinessPolicy.can_update(user=request.user, business=business):
    raise PermissionDenied(
        message="You don't have permission to update this business",
        action="update",
        resource="BusinessAccount",
    )
```

---

## 10. File Map

```
apps/organization/
├── __init__.py
├── apps.py
├── INDEX.md                    ← This file
├── platform/
│   ├── __init__.py
│   ├── models.py               # PlatformAccount, PlatformProfile
│   ├── selectors.py            # Read queries
│   ├── services.py             # Write operations
│   ├── policies.py             # Authorization
│   ├── serializers.py          # I/O serializers
│   ├── views.py                # API views
│   ├── urls.py                 # /api/v1/platform/*
│   └── admin.py                # Django admin
├── business/
│   ├── __init__.py
│   ├── models.py               # BusinessAccount, BusinessProfile, SlugHistory
│   ├── selectors.py            # Read queries + slug redirect
│   ├── services.py             # Write operations
│   ├── policies.py             # Authorization (RBAC stubs)
│   ├── serializers.py          # I/O serializers
│   ├── views.py                # API views
│   ├── urls.py                 # /api/v1/business/*
│   └── admin.py                # Django admin
├── tests/
│   ├── __init__.py
│   ├── factories.py            # Factory-boy factories
│   ├── conftest.py             # Pytest fixtures
│   ├── platform/
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   └── test_views.py
│   └── business/
│       ├── test_models.py
│       ├── test_services.py
│       └── test_views.py
└── migrations/
    ├── __init__.py
    ├── 0001_initial.py
    └── 0002_create_platform_singleton.py
```

---

## 11. Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| Platform Models | 9 | Pass |
| Platform Services | 10 | Pass |
| Platform Views | 11 | Pass |
| Business Models | 17 | Pass |
| Business Services | 21 | Pass |
| Business Views | 30 | Pass |
| **Total** | **98** | **Pass** |

---

## Changelog

### v1.0.1 (2026-02-09)
- Output serializers now inherit from `BaseOutputSerializer`
- Permissions imported from `apps.core.permissions`
- Views pass `context={'request': request}` to output serializers
- Added Code Patterns section to documentation

### v1.0.0 (2026-02-09)
- Initial implementation
- Platform singleton with profile
- Business multi-tenancy with profiles
- Slug history for redirects
- Full audit logging
- 98 tests passing
