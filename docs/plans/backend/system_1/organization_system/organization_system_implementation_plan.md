# Organization System Implementation Plan

## Multi-Tenant Platform - System 1 of 4

**Version:** 1.2
**Date:** February 8, 2026
**Status:** Ready for Implementation

> **v1.2 Changes**: Updated RBAC integration stubs to reflect RBAC v1.2 architecture. ActorContext
> is now a pure data structure in `apps/core/types.py`. Use `RBACService.build_actor_context()` to
> construct instances with resolved permissions. Added 3-stage ownership transfer audit trail documentation.

---

## Critical Invariants

> **These rules are non-negotiable and enforced at the database level.**

### 1. Platform Singleton (DB-Enforced)
The platform account is a singleton enforced by a **unique constraint on `singleton_key=1`**, not application logic. This prevents race conditions and accidental duplicate rows.

### 2. Slug Uniqueness (Forever, No Reuse)
Business slugs are **globally unique forever**. Once a slug is used (even if changed later), it cannot be reused by any other business. Old slugs always redirect to the current slug. This is enforced by:
- `BusinessAccount.slug` unique constraint
- `BusinessSlugHistory.old_slug` unique constraint

### 3. Business Ownership on Creation
The **authenticated user who creates a BusinessAccount is the initial owner**. RBAC initialization must create an owner membership for that user. Ownership is tracked via `Membership.is_owner=True`, not by role alone.

---

## Executive Summary

This plan outlines the implementation of the Organization System, which manages two tenant types:
- **PlatformAccount** (singleton): Root governance entity for the platform
- **BusinessAccount** (many): Multi-tenant businesses

The system follows the established layered architecture pattern: models → managers → selectors → services → serializers → views → URLs.

---

## 1. Prerequisites

### 1.1 Required Enums in `apps/core/constants.py` (Create New File)

```python
# backend/apps/core/constants.py

from django.db import models


class AccountType(models.TextChoices):
    """Types of accounts in the system."""
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"


class ContextType(models.TextChoices):
    """Context types for Transaction system integration."""
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"
    USER = "user", "User"


class OwnerType(models.TextChoices):
    """Owner types for Form Builder integration."""
    SYSTEM = "system", "System"
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"


class FormScope(models.TextChoices):
    """Scope for forms."""
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"


class PermissionScope(models.TextChoices):
    """Permission scope for RBAC integration."""
    BUSINESS = "business", "Business Only"
    PLATFORM_ONLY = "platform_only", "Platform Only"
    GLOBAL_ONLY = "global_only", "Global Only"
    PLATFORM_AND_GLOBAL = "platform_and_global", "Platform and Global"


class MembershipStatus(models.TextChoices):
    """Membership status for RBAC integration."""
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    LEFT = "left", "Left"
    REMOVED = "removed", "Removed"
    BANNED = "banned", "Banned"


# Business-specific enums
class BusinessType(models.TextChoices):
    """Types of business entities."""
    SOLE_PROPRIETORSHIP = "sole_proprietorship", "Sole Proprietorship"
    PARTNERSHIP = "partnership", "Partnership"
    LLC = "llc", "LLC"
    CORPORATION = "corporation", "Corporation"
    NONPROFIT = "nonprofit", "Nonprofit"
    COOPERATIVE = "cooperative", "Cooperative"
    OTHER = "other", "Other"


class BusinessStatus(models.TextChoices):
    """Business account status."""
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"
    DELETED = "deleted", "Deleted"


class VerificationStatus(models.TextChoices):
    """Business verification status."""
    UNVERIFIED = "unverified", "Unverified"
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class CompanySize(models.TextChoices):
    """Company size ranges."""
    SIZE_1 = "1", "1 employee"
    SIZE_2_10 = "2-10", "2-10 employees"
    SIZE_11_50 = "11-50", "11-50 employees"
    SIZE_51_200 = "51-200", "51-200 employees"
    SIZE_201_500 = "201-500", "201-500 employees"
    SIZE_500_PLUS = "500+", "500+ employees"
```

### 1.2 New AuditLog Actions

Add to `apps/core/observability/audit/models.py` - `AuditLog.Action` enum:

```python
# Organization - Platform
PLATFORM_CONFIGURED = "org.platform.configured", "Platform Configured"
PLATFORM_SETTINGS_UPDATED = "org.platform.settings_updated", "Platform Settings Updated"
PLATFORM_PROFILE_UPDATED = "org.platform.profile_updated", "Platform Profile Updated"

# Organization - Business
BUSINESS_CREATED = "org.business.created", "Business Created"
BUSINESS_UPDATED = "org.business.updated", "Business Updated"
BUSINESS_SUSPENDED = "org.business.suspended", "Business Suspended"
BUSINESS_REACTIVATED = "org.business.reactivated", "Business Reactivated"
BUSINESS_ARCHIVED = "org.business.archived", "Business Archived"
BUSINESS_DELETED = "org.business.deleted", "Business Deleted"
BUSINESS_SLUG_CHANGED = "org.business.slug_changed", "Business Slug Changed"
BUSINESS_PROFILE_UPDATED = "org.business.profile_updated", "Business Profile Updated"

# Verification
VERIFICATION_APPROVED = "org.verification.approved", "Verification Approved"
VERIFICATION_REJECTED = "org.verification.rejected", "Verification Rejected"

# Ownership
OWNERSHIP_TRANSFER_INITIATED = "org.ownership.transfer_initiated", "Ownership Transfer Initiated"

# NOTE: Ownership transfer has a 3-stage audit trail:
# 1. OWNERSHIP_TRANSFER_INITIATED (Organization system) - When transaction created
# 2. OWNERSHIP_TRANSFERRED (RBAC system) - When transaction accepted
# 3. OWNER_MEMBERSHIP_CREATED (RBAC system) - When new owner membership created
# This ensures complete traceability of the ownership transfer process across systems.
```

---

## 2. App Structure

```
backend/apps/organization/
    __init__.py
    apps.py

    platform/
        __init__.py
        models.py           # PlatformAccount, PlatformProfile
        managers.py         # PlatformAccountManager
        selectors.py        # PlatformAccountSelector
        services.py         # PlatformAccountService, PlatformProfileService
        policies.py         # PlatformPolicy
        serializers.py      # Input/Output serializers
        views.py            # PlatformAccountView, PlatformProfileView
        urls.py             # URL routing
        admin.py            # Admin configuration

    business/
        __init__.py
        models.py           # BusinessAccount, BusinessProfile, BusinessSlugHistory
        managers.py         # BusinessAccountManager
        selectors.py        # BusinessAccountSelector, BusinessProfileSelector
        services.py         # BusinessAccountService, BusinessProfileService, VerificationOutcomeHandler
        policies.py         # BusinessPolicy
        serializers.py      # Input/Output serializers
        views.py            # Business CRUD views
        urls.py             # URL routing
        admin.py            # Admin configuration

    tests/
        __init__.py
        conftest.py         # Shared test fixtures
        factories.py        # Factory-boy factories

        platform/
            __init__.py
            test_models.py
            test_services.py
            test_views.py

        business/
            __init__.py
            test_models.py
            test_services.py
            test_views.py
```

---

## 3. Model Definitions

### 3.1 Platform Models (`apps/organization/platform/models.py`)

```python
"""
Platform Models - Singleton platform account and profile.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditModel


class PlatformAccount(AuditModel):
    """
    Singleton model for platform governance.

    INVARIANT: Only one instance can exist - enforced by DB unique constraint on singleton_key.
    This prevents race conditions and accidental duplicates under concurrency.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # DB-level singleton enforcement - unique constraint guarantees only one row
    singleton_key = models.PositiveSmallIntegerField(
        default=1,
        unique=True,
        editable=False,
        help_text="Singleton enforcement - always 1"
    )

    is_configured = models.BooleanField(default=False, help_text="Whether initial setup is complete")
    settings = models.JSONField(default=dict, blank=True, help_text="Platform-wide settings")

    class Meta:
        db_table = "platform_account"
        verbose_name = "Platform Account"
        verbose_name_plural = "Platform Accounts"
        constraints = [
            models.CheckConstraint(
                check=models.Q(singleton_key=1),
                name="platform_account_singleton"
            )
        ]

    def __str__(self):
        return f"Platform Account ({self.id})"

    def save(self, *args, **kwargs):
        self.singleton_key = 1  # Always enforce
        super().save(*args, **kwargs)


class PlatformProfile(models.Model):
    """Platform branding and public-facing information."""
    platform = models.OneToOneField(PlatformAccount, on_delete=models.CASCADE, primary_key=True, related_name="profile")
    name = models.CharField(max_length=255, help_text="Platform name")
    tagline = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="platform/logo/", blank=True, null=True)
    favicon = models.ImageField(upload_to="platform/favicon/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#000000")
    secondary_color = models.CharField(max_length=7, default="#ffffff")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    social_links = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_profile"
        verbose_name = "Platform Profile"
        verbose_name_plural = "Platform Profiles"

    def __str__(self):
        return f"Platform Profile: {self.name}"
```

### 3.2 Business Models (`apps/organization/business/models.py`)

```python
"""
Business Models - Multi-tenant business accounts.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from apps.core.models import AuditModel
from apps.core.models.managers import SoftDeleteManager
from apps.core.constants import BusinessType, BusinessStatus, VerificationStatus, CompanySize


class BusinessAccountManager(SoftDeleteManager):
    """
    Manager for BusinessAccount with common query patterns.

    Inherits from SoftDeleteManager to automatically filter is_deleted=False.
    """

    def get_queryset(self):
        """Return base queryset with soft-delete filtering."""
        return super().get_queryset()  # Already filters is_deleted=False

    def active(self):
        """Return active (non-deleted, active status) businesses."""
        return self.get_queryset().filter(status=BusinessStatus.ACTIVE)

    def verified(self):
        """Return active verified businesses."""
        return self.active().filter(verification_status=VerificationStatus.VERIFIED)

    def pending_verification(self):
        """Return active businesses with pending verification."""
        return self.active().filter(verification_status=VerificationStatus.PENDING)


class BusinessAccount(AuditModel):
    """Multi-tenant business account."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)

    # Legal information
    legal_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, blank=True, default="")
    tax_id = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    legal_address = models.TextField(blank=True, default="")

    # Classification
    business_type = models.CharField(max_length=30, choices=BusinessType.choices, default=BusinessType.OTHER)

    # Status
    status = models.CharField(max_length=20, choices=BusinessStatus.choices, default=BusinessStatus.PENDING, db_index=True)

    # Verification
    verification_status = models.CharField(max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_businesses")

    # Settings
    settings = models.JSONField(default=dict, blank=True)

    objects = BusinessAccountManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "business_account"
        verbose_name = "Business Account"
        verbose_name_plural = "Business Accounts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "is_deleted"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"{self.legal_name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.legal_name)
        super().save(*args, **kwargs)


class BusinessProfile(models.Model):
    """Public-facing business profile."""
    business = models.OneToOneField(BusinessAccount, on_delete=models.CASCADE, primary_key=True, related_name="profile")
    display_name = models.CharField(max_length=255)
    tagline = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="business/logos/%Y/%m/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="business/covers/%Y/%m/", blank=True, null=True)
    website = models.URLField(blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    company_size = models.CharField(max_length=20, choices=CompanySize.choices, blank=True, default="")
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True, help_text="Form Builder extensions")
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "business_profile"
        verbose_name = "Business Profile"
        verbose_name_plural = "Business Profiles"

    def __str__(self):
        return f"Profile: {self.display_name}"


class BusinessSlugHistory(models.Model):
    """
    Tracks slug changes for URL redirects.

    INVARIANT: old_slug is globally unique - old slugs can NEVER be reused.
    This ensures permanent redirects work and prevents slug hijacking.
    """
    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name="slug_history")
    old_slug = models.SlugField(max_length=100, unique=True, db_index=True)  # UNIQUE - no reuse ever
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "business_slug_history"
        verbose_name = "Business Slug History"
        verbose_name_plural = "Business Slug Histories"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.old_slug} -> {self.business.slug}"
```

---

## 4. Key Services

### 4.1 Business Account Service (Key Methods)

**Ownership Rule:** The `owner` parameter in `create_business()` is the authenticated user from `request.user`. This user becomes the initial owner via RBAC membership creation.

**Slug Validation Rule:** When creating or updating a slug, the service MUST check:
1. `BusinessAccount.objects.filter(slug=new_slug)` - not used by active business
2. `BusinessSlugHistory.objects.filter(old_slug=new_slug)` - not a retired slug

If either check finds a match, raise `ConflictError`.

| Method | Purpose | RBAC Integration |
|--------|---------|-----------------|
| `create_business(owner=request.user, ...)` | Create business + profile, owner becomes initial owner | **STUB:** Will call `RBACService.initialize_business_account(owner=owner)` |
| `update()` | Update business fields | - |
| `update_slug()` | Change slug with redirect tracking (old slug stored in history, can never be reused) | - |
| `suspend()` | Platform suspends business | Policy check required |
| `reactivate()` | Reactivate suspended business | Policy check required |
| `archive()` | Owner archives business | Owner only |
| `soft_delete()` | Soft delete business | Owner/Superuser only |

### 4.2 Verification Integration with Transaction System

**Note:** The `VerificationOutcomeHandler` is defined in `apps/transaction/outcome_handlers.py` (Transaction System). The Organization System provides the service methods that the handler calls.

When a business verification transaction completes, the Transaction System calls:

| Transaction Handler Method | Calls Organization Service | Result |
|----------------------------|----------------------------|--------|
| `VerificationOutcomeHandler.handle_accepted()` | `BusinessService.update_verification_status()` | Set `verification_status=VERIFIED`, `verified_at`, `verified_by` |
| `VerificationOutcomeHandler.handle_denied()` | `BusinessService.update_verification_status()` | Set `verification_status=REJECTED` |

**Required Service Method:**

`BusinessService.update_verification_status()` must be implemented to support these handlers.

---

## 5. URL Routing

### 5.1 Platform URLs (`/api/v1/platform/`)

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/account/` | GET | Authenticated | Get platform account |
| `/account/` | POST | Superuser | Initial configuration |
| `/profile/` | GET | Authenticated | Get platform profile |
| `/profile/` | PATCH | Staff | Update platform profile |
| `/settings/` | PATCH | Superuser | Update platform settings |

### 5.2 Business URLs (`/api/v1/business/`)

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/` | GET | Authenticated | List active businesses |
| `/` | POST | Authenticated | Create new business (request.user becomes owner) |
| `/my/` | GET | Authenticated | List user's businesses |
| `/id/{uuid}/` | GET | Authenticated | Get business by UUID |
| `/{slug}/` | GET | Authenticated | Get business by slug |
| `/{slug}/` | PATCH | Owner/Staff | Update business |
| `/{slug}/` | DELETE | Owner/Superuser | Soft delete business |
| `/{slug}/profile/` | GET | Authenticated | Get business profile |
| `/{slug}/profile/` | PATCH | Owner/Staff | Update business profile |

---

## 6. Implementation Order

### Phase 1: Foundation
1. Create `apps/core/constants.py` with all enums
2. Add AuditLog actions to `apps/core/observability/audit/models.py`
3. Create organization app structure (directories, `__init__.py` files)
4. Create `apps/organization/apps.py`

### Phase 2: Platform Module
5. Create platform models (`platform/models.py`)
6. Create platform selectors (`platform/selectors.py`)
7. Create platform services (`platform/services.py`)
8. Create platform serializers (`platform/serializers.py`)
9. Create platform views (`platform/views.py`)
10. Create platform URLs (`platform/urls.py`)
11. Create platform admin (`platform/admin.py`)

### Phase 3: Business Module
12. Create business models (`business/models.py`)
13. Create business selectors (`business/selectors.py`)
14. Create business services (`business/services.py`)
15. Create business serializers (`business/serializers.py`)
16. Create business views (`business/views.py`)
17. Create business URLs (`business/urls.py`)
18. Create business admin (`business/admin.py`)

### Phase 4: Integration
19. Add `apps.organization` to `INSTALLED_APPS` in `backend_core/settings/base.py`
20. Register URLs in `backend_core/urls.py`
21. Run `makemigrations organization`
22. Create data migration for Platform singleton
23. Run `migrate`

### Phase 5: Testing
24. Create test factories (`tests/factories.py`)
25. Create test fixtures (`tests/conftest.py`)
26. Create platform tests
27. Create business tests
28. Run `make check`

---

## 7. Test Factories

```python
# apps/organization/tests/factories.py

import factory
from factory.django import DjangoModelFactory
from apps.organization.platform.models import PlatformAccount, PlatformProfile
from apps.organization.business.models import BusinessAccount, BusinessProfile
from apps.core.constants import BusinessType, BusinessStatus, VerificationStatus


class PlatformAccountFactory(DjangoModelFactory):
    class Meta:
        model = PlatformAccount
        django_get_or_create = ("singleton_key",)  # Ensures singleton in tests

    singleton_key = 1  # DB constraint requires this
    is_configured = True
    settings = {}


class PlatformProfileFactory(DjangoModelFactory):
    class Meta:
        model = PlatformProfile

    platform = factory.SubFactory(PlatformAccountFactory)
    name = "Test Platform"
    tagline = "Your Test Platform"
    contact_email = "platform@example.com"


class BusinessAccountFactory(DjangoModelFactory):
    class Meta:
        model = BusinessAccount

    legal_name = factory.Sequence(lambda n: f"Test Business {n}")
    slug = factory.LazyAttribute(lambda obj: obj.legal_name.lower().replace(" ", "-"))
    country = "US"
    business_type = BusinessType.LLC
    status = BusinessStatus.ACTIVE
    verification_status = VerificationStatus.UNVERIFIED


class BusinessProfileFactory(DjangoModelFactory):
    class Meta:
        model = BusinessProfile

    business = factory.SubFactory(BusinessAccountFactory)
    display_name = factory.LazyAttribute(lambda obj: obj.business.legal_name)
    is_public = True
```

---

## 8. Migration Strategy

### Data Migration for Platform Singleton

```python
# 0002_create_platform_singleton.py

from django.db import migrations

def create_platform_singleton(apps, schema_editor):
    PlatformAccount = apps.get_model('organization', 'PlatformAccount')
    PlatformProfile = apps.get_model('organization', 'PlatformProfile')

    if not PlatformAccount.objects.exists():
        # singleton_key=1 is enforced by unique + check constraints
        platform = PlatformAccount.objects.create(
            singleton_key=1,
            is_configured=False,
            settings={}
        )
        PlatformProfile.objects.create(platform=platform, name="Platform")

def reverse_migration(apps, schema_editor):
    PlatformAccount = apps.get_model('organization', 'PlatformAccount')
    PlatformAccount.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [('organization', '0001_initial')]
    operations = [migrations.RunPython(create_platform_singleton, reverse_migration)]
```

---

## 9. RBAC Integration Points (Stubs for Future)

### In `BusinessAccountService.create_business()`:

```python
# STUB: RBAC Integration Point
# When RBAC is implemented, uncomment and update:
#
# from apps.rbac.services import RBACService
#
# RBACService.initialize_business_account(
#     business_id=business.id,
#     owner=owner,  # request.user - becomes initial owner
#     request=request
# )
#
# This will:
# 1. Create predefined roles (Owner level 0, Base Member level 10)
# 2. Create owner membership for the user with is_owner=True
# 3. Return the created Membership instance
#
# INVARIANT: The `owner` param is the authenticated user (request.user).
# This user MUST get a Membership with is_owner=True.
# Ownership is determined by Membership.is_owner flag, NOT by role name.
#
# NOTE: To create ActorContext from membership, use:
#   actor_context = RBACService.build_actor_context(membership=membership, request=request)
# Never construct ActorContext directly from membership - use RBACService to ensure
# permissions are properly resolved and cached.
```

### In `BusinessAccountSelector.list_by_owner()` and `list_by_member()`:

```python
# STUB: RBAC Integration Point
# When RBAC is implemented, query memberships:
#
# from apps.rbac.models import Membership
# from apps.core.constants import AccountType, MembershipStatus
#
# membership_business_ids = Membership.objects.filter(
#     user=user,
#     account_type=AccountType.BUSINESS,
#     status=MembershipStatus.ACTIVE
# ).values_list('account_id', flat=True)
#
# return BusinessAccount.objects.filter(id__in=membership_business_ids)
```

---

## 10. Files to Create (Summary)

| File | Purpose |
|------|---------|
| `backend/apps/core/constants.py` | All shared enums |
| `backend/apps/organization/__init__.py` | App init |
| `backend/apps/organization/apps.py` | App config |
| `backend/apps/organization/platform/models.py` | PlatformAccount, PlatformProfile |
| `backend/apps/organization/platform/selectors.py` | Read-only queries |
| `backend/apps/organization/platform/services.py` | Business logic |
| `backend/apps/organization/platform/serializers.py` | API serializers |
| `backend/apps/organization/platform/views.py` | API views |
| `backend/apps/organization/platform/urls.py` | URL routing |
| `backend/apps/organization/platform/admin.py` | Admin config |
| `backend/apps/organization/business/models.py` | BusinessAccount, BusinessProfile, BusinessSlugHistory |
| `backend/apps/organization/business/selectors.py` | Read-only queries |
| `backend/apps/organization/business/services.py` | Business logic + VerificationOutcomeHandler |
| `backend/apps/organization/business/serializers.py` | API serializers |
| `backend/apps/organization/business/views.py` | API views |
| `backend/apps/organization/business/urls.py` | URL routing |
| `backend/apps/organization/business/admin.py` | Admin config |
| `backend/apps/organization/tests/factories.py` | Factory-boy factories |
| `backend/apps/organization/tests/conftest.py` | Pytest fixtures |
| `backend/apps/organization/tests/platform/test_*.py` | Platform tests |
| `backend/apps/organization/tests/business/test_*.py` | Business tests |

---

## 11. Verification Checklist

Before completing implementation:

### Critical Invariants (DB-Level)
- [ ] `PlatformAccount.singleton_key` has unique constraint + check constraint
- [ ] `BusinessAccount.slug` has unique constraint
- [ ] `BusinessSlugHistory.old_slug` has unique constraint (prevents slug reuse)
- [ ] Business creation service passes `owner=request.user` to RBAC

### Standard Checks
- [ ] All enums created in `apps/core/constants.py`
- [ ] AuditLog actions added to enum
- [ ] `apps.organization` added to `INSTALLED_APPS`
- [ ] URLs registered in `backend_core/urls.py`:
  ```python
  path("api/v1/platform/", include("apps.organization.platform.urls")),
  path("api/v1/business/", include("apps.organization.business.urls")),
  ```
- [ ] Migrations created and applied
- [ ] Platform singleton created via data migration
- [ ] All services use `get_logger(__name__)`
- [ ] All write operations use `AuditService.log()`
- [ ] All selectors raise `NotFound` appropriately
- [ ] All views use proper permissions
- [ ] Factories registered in `conftest.py`
- [ ] Tests pass: `make test`
- [ ] Coverage ≥ 80%
- [ ] Lint passes: `make check`

### Invariant Tests (Must Pass)
- [ ] Test: Creating second PlatformAccount raises IntegrityError
- [ ] Test: Creating business with existing slug raises ConflictError
- [ ] Test: Creating business with old slug from history raises ConflictError
- [ ] Test: Business creator gets owner membership (via RBAC stub)

---

## 12. Testing Commands

```bash
# Run all tests
make test

# Run organization tests only
pytest backend/apps/organization/tests/ -v

# Run with coverage
pytest backend/apps/organization/tests/ --cov=apps.organization --cov-report=term-missing

# Full check (lint + tests)
make check
```

---

## 13. Critical Reference Files

| File | Purpose |
|------|---------|
| `backend/apps/core/models/base.py` | Base model classes to inherit |
| `backend/apps/core/exceptions/domain.py` | Core exceptions (NotFound, etc.) |
| `backend/apps/core/observability/audit/models.py` | AuditLog model for actions |
| `backend/apps/users/services.py` | Pattern reference for services |
| `backend/apps/auth/views.py` | Pattern reference for views |
| `backend_core/settings/base.py` | INSTALLED_APPS location |
| `backend_core/urls.py` | URL registration location |

---

*End of Implementation Plan*
