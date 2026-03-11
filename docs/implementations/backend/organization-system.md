# Organization System — Implementation Reference

**Version:** v1
**Last Updated:** 2026-02-24
**Status:** Implemented

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  API Layer                                                       │
│  Business: 9 views (ListCreate, MyList, Detail, ById,            │
│            SlugUpdate, Profile, Suspend, Reactivate, Archive)    │
│  Platform: 3 views (Account, Profile, Settings)                  │
├──────────────────────────────────────────────────────────────────┤
│  Serializers                                                     │
│  Business: 4 input + 4 output                                    │
│  Platform: 3 input + 3 output                                    │
├──────────────────────────────────────────────────────────────────┤
│  Service Layer                                                   │
│  BusinessAccountService: create, update, update_slug, suspend,   │
│                          reactivate, archive, soft_delete,        │
│                          update_verification_status               │
│  BusinessProfileService: update                                  │
│  PlatformAccountService: configure, update_settings              │
│  PlatformProfileService: update                                  │
├─────────────────────┬────────────────────────────────────────────┤
│  Policies            │  Selectors                                 │
│  BusinessPolicy      │  BusinessAccountSelector (10 methods)      │
│  (11 methods)        │  BusinessProfileSelector (2 methods)       │
│  PlatformPolicy      │  PlatformAccountSelector (3 methods)       │
│  (4 methods)         │  PlatformProfileSelector (1 method)        │
├─────────────────────┴────────────────────────────────────────────┤
│  Data Layer                                                      │
│  BusinessAccount (UUID, soft-delete, 4 indexes)                  │
│  BusinessProfile (OneToOne, PK=business)                         │
│  BusinessSlugHistory (BigAutoField PK, unique old_slug)          │
│  PlatformAccount (Singleton, UUID, CheckConstraint)              │
│  PlatformProfile (OneToOne, PK=platform)                         │
├──────────────────────────────────────────────────────────────────┤
│  Constants (apps/core/constants.py)                              │
│  AccountType, BusinessType, BusinessStatus, VerificationStatus,  │
│  CompanySize, OwnerType                                          │
└──────────────────────────────────────────────────────────────────┘

External dependencies:
  → apps.rbac (RBACService.initialize_business_account, initialize_platform_account)
  → apps.core (AuditModel, AuditService, exceptions, pagination, constants)
  → apps.users (User model, FK references)
  → apps.transaction (VerificationOutcomeHandler calls update_verification_status)
```

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Two parallel account types | PlatformAccount (singleton) + BusinessAccount (multi-tenant) | Separates platform governance from business operations; each has its own lifecycle and permissions |
| Subpackage architecture | `organization/business/` and `organization/platform/` | Keeps each account type self-contained with its own models, selectors, services, policies, serializers, views, urls, admin |
| Singleton PlatformAccount | CheckConstraint(`singleton_key=1`) + `save()` override | Guarantees exactly one platform account row; prevents accidental duplication |
| Slug-based routing | BusinessAccount addressed by slug with UUID fallback | SEO-friendly URLs; slug history enables 301 redirects when slugs change |
| Slug history with uniqueness | BusinessSlugHistory with `unique=True` on `old_slug` | Old slugs can never be reused by any business; prevents confusion and enables permanent redirects |
| OneToOne profile pattern | Separate BusinessProfile and PlatformProfile models | Keeps legal/account data separate from public-facing display data; allows independent update policies |
| Soft-delete via base model | Inherits `AuditModel` with `is_deleted` | Consistent with other apps; `objects` manager auto-filters deleted records |
| STUB authorization policies | BusinessPolicy uses `created_by` checks instead of RBAC | Placeholder until RBAC membership integration is complete; clearly marked as STUBs |

---

## 3. Data Layer

### 3.1 BusinessAccount

Location: `apps/organization/business/models.py`

Inherits: `AuditModel` = `UUIDModel` (UUID pk) + timestamps (created_at, updated_at) + soft-delete (is_deleted, deleted_at, deleted_by) + audit (created_by, updated_by)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk) | Auto-generated |
| `slug` | SlugField(100, unique=True) | URL-friendly identifier; indexed |
| `legal_name` | CharField(255) | Official business name |
| `registration_number` | CharField(100, blank) | Government registration number |
| `tax_id` | CharField(100, blank) | Tax identification number |
| `country` | CharField(2) | ISO 3166-1 alpha-2 code; indexed |
| `legal_address` | TextField(blank) | Full legal address |
| `business_type` | CharField(choices=BusinessType, default=OTHER) | SOLE_PROPRIETORSHIP, PARTNERSHIP, LLC, CORPORATION, NONPROFIT, COOPERATIVE, OTHER |
| `status` | CharField(choices=BusinessStatus, default=PENDING) | PENDING, ACTIVE, SUSPENDED, ARCHIVED, DELETED |
| `verification_status` | CharField(choices=VerificationStatus, default=UNVERIFIED) | UNVERIFIED, PENDING, VERIFIED, REJECTED, EXPIRED; indexed |
| `verified_at` | DateTimeField(null) | When verification was completed |
| `verified_by` | FK→User(SET_NULL, null) | Staff member who verified |
| `settings` | JSONField(default=dict) | Extensible settings store |

**Indexes:**
- `slug`
- `(status, is_deleted)`
- `verification_status`
- `country`

**Manager:** `objects = BusinessAccountManager()` with custom QuerySet methods:
- `active()` — filters `status=ACTIVE, is_deleted=False`
- `verified()` — filters `verification_status=VERIFIED`
- `pending_verification()` — filters `verification_status=PENDING`

### 3.2 BusinessProfile

Location: `apps/organization/business/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `business` | OneToOneField(BusinessAccount, CASCADE, related_name="profile") | Primary key |
| `display_name` | CharField(255) | Public-facing display name |
| `tagline` | CharField(500, blank) | Short business tagline |
| `description` | TextField(blank) | Full business description |
| `logo` | ImageField(upload_to="business/logos/%Y/%m/", blank, null) | Business logo |
| `cover_image` | ImageField(upload_to="business/covers/%Y/%m/", blank, null) | Cover/banner image |
| `website` | URLField(blank) | Business website URL |
| `contact_email` | EmailField(blank) | Public contact email |
| `contact_phone` | CharField(20, blank) | Public contact phone |
| `industry` | CharField(100, blank) | Industry classification |
| `company_size` | CharField(choices=CompanySize, blank) | 1, 2-10, 11-50, 51-200, 201-500, 500+ |
| `founded_year` | PositiveIntegerField(null) | Year established |
| `social_links` | JSONField(default=dict) | Social media URLs |
| `custom_fields` | JSONField(default=dict) | Form Builder extensions |
| `is_public` | BooleanField(default=True) | Whether profile is publicly visible |
| `created_at` | DateTimeField(auto_now_add) | Profile creation timestamp |
| `updated_at` | DateTimeField(auto_now) | Last update timestamp |

### 3.3 BusinessSlugHistory

Location: `apps/organization/business/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | BigAutoField(pk) | Auto-generated |
| `business` | FK→BusinessAccount(CASCADE, related_name="slug_history") | Owning business |
| `old_slug` | SlugField(100, unique=True) | Previous slug; unique across all businesses — old slugs can never be reused |
| `changed_at` | DateTimeField(auto_now_add) | When the slug was changed |

### 3.4 PlatformAccount

Location: `apps/organization/platform/models.py`

Inherits: `AuditModel` (same as BusinessAccount)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk) | Auto-generated |
| `singleton_key` | PositiveSmallIntegerField(default=1, unique=True, editable=False) | Enforces single row |
| `is_configured` | BooleanField(default=False) | Set to True after one-time configuration |
| `settings` | JSONField(default=dict) | Platform-wide settings |

**Constraints:**
- `CheckConstraint`: `singleton_key=1`
- `save()` override always resets `singleton_key` to 1

### 3.5 PlatformProfile

Location: `apps/organization/platform/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `platform` | OneToOneField(PlatformAccount, CASCADE, related_name="profile") | Primary key |
| `name` | CharField(255) | Platform name |
| `tagline` | CharField(500, blank) | Platform tagline |
| `description` | TextField(blank) | Platform description |
| `logo` | ImageField(upload_to="platform/logo/", blank, null) | Platform logo |
| `favicon` | ImageField(upload_to="platform/favicon/", blank, null) | Browser favicon |
| `primary_color` | CharField(7, default="#000000") | Brand primary color (hex) |
| `secondary_color` | CharField(7, default="#ffffff") | Brand secondary color (hex) |
| `contact_email` | EmailField(blank) | Platform contact email |
| `contact_phone` | CharField(20, blank) | Platform contact phone |
| `address` | TextField(blank) | Platform physical address |
| `social_links` | JSONField(default=dict) | Social media URLs |
| `created_at` | DateTimeField(auto_now_add) | Profile creation timestamp |
| `updated_at` | DateTimeField(auto_now) | Last update timestamp |

### Migrations

- `0001_initial` — Creates all five tables: business_account, business_profile, business_slug_history, platform_account, platform_profile with all indexes and constraints
- `0002_create_platform_singleton` — Data migration creating the singleton PlatformAccount row and its associated PlatformProfile

---

## 4. Service Layer

### 4.1 BusinessAccountService

Location: `apps/organization/business/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_business` | owner, legal_name, country, slug?, business_type?, ... | BusinessAccount | `@transaction.atomic`. Creates BusinessAccount + BusinessProfile. Calls `RBACService.initialize_business_account()`. Auto-generates slug from legal_name if not provided. Audits `BUSINESS_CREATED` |
| `update` | business, legal_name?, ..., actor | BusinessAccount | Updates mutable fields. Audits `BUSINESS_UPDATED` |
| `update_slug` | business, new_slug, actor | BusinessAccount | Creates BusinessSlugHistory entry for old slug. Audits `BUSINESS_SLUG_CHANGED` |
| `suspend` | business, reason, actor | BusinessAccount | Sets status=SUSPENDED. Audits `BUSINESS_SUSPENDED` |
| `reactivate` | business, actor | BusinessAccount | Sets status=ACTIVE. Audits `BUSINESS_REACTIVATED` |
| `archive` | business, actor | BusinessAccount | Sets status=ARCHIVED. Audits `BUSINESS_ARCHIVED` |
| `soft_delete` | business, actor | BusinessAccount | Sets status=DELETED, calls soft-delete. Audits `BUSINESS_DELETED` |
| `update_verification_status` | business, status, actor | BusinessAccount | Called by Transaction system's VerificationOutcomeHandler. Audits `VERIFICATION_APPROVED` or `VERIFICATION_REJECTED` |

### 4.2 BusinessProfileService

Location: `apps/organization/business/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `update` | profile, display_name?, ..., actor | BusinessProfile | Updates profile fields. Audits `BUSINESS_PROFILE_UPDATED` |

### 4.3 PlatformAccountService

Location: `apps/organization/platform/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `configure` | name, settings?, actor | PlatformAccount | One-time setup. Creates PlatformProfile, sets `is_configured=True`. Calls `RBACService.initialize_platform_account()`. Audits `PLATFORM_CONFIGURED` |
| `update_settings` | settings, actor | PlatformAccount | Merges new settings into existing settings dict. Audits `PLATFORM_SETTINGS_UPDATED` |

### 4.4 PlatformProfileService

Location: `apps/organization/platform/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `update` | name?, ..., actor | PlatformProfile | Updates profile fields. Audits `PLATFORM_PROFILE_UPDATED` |

### 4.5 Selectors

**BusinessAccountSelector** — Location: `apps/organization/business/selectors.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_by_id` | business_id, include_deleted=False | BusinessAccount | Raises `NotFound` |
| `get_by_slug` | slug, include_deleted=False | BusinessAccount | Raises `NotFound` |
| `get_by_slug_or_redirect` | slug | tuple[BusinessAccount, str\|None] | Checks slug history; returns redirect slug if business was found via old slug |
| `list_active` | — | QuerySet | Uses manager's `active()` |
| `list_verified` | — | QuerySet | Uses manager's `verified()` |
| `list_pending_verification` | — | QuerySet | Uses manager's `pending_verification()` |
| `list_by_country` | country | QuerySet | Filters active businesses by ISO country code |
| `slug_exists` | slug, exclude_business_id? | bool | Checks both current slugs and BusinessSlugHistory |
| `list_by_owner` | user | QuerySet | **STUB**: filters by `created_by`; will use RBAC membership |
| `list_by_member` | user | QuerySet | **STUB**: filters by `created_by`; will use RBAC membership |

**BusinessProfileSelector** — Location: `apps/organization/business/selectors.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_by_business_id` | business_id | BusinessProfile | Raises `NotFound` |
| `list_public` | — | QuerySet | Filters `is_public=True` |

**PlatformAccountSelector** — Location: `apps/organization/platform/selectors.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get` | — | PlatformAccount | With `select_related("profile")`; raises `NotFound` |
| `exists` | — | bool | Whether singleton row exists |
| `is_configured` | — | bool | Whether `is_configured=True` |

**PlatformProfileSelector** — Location: `apps/organization/platform/selectors.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get` | — | PlatformProfile | Raises `NotFound` |

### 4.6 Policies

**BusinessPolicy** — Location: `apps/organization/business/policies.py`

| Method | Args | Behavior |
|--------|------|----------|
| `can_create` | user | Any authenticated user |
| `can_view` | user, business | Authenticated + (staff OR business is active) |
| `can_update` | user, business | **STUB**: staff OR `created_by` match |
| `can_update_slug` | user, business | **STUB**: `created_by` match |
| `can_delete` | user, business | **STUB**: superuser OR `created_by` match |
| `can_archive` | user, business | **STUB**: `created_by` match |
| `can_suspend` | user, business | Staff/superuser only |
| `can_reactivate` | user, business | Staff/superuser only |
| `can_verify` | user, business | Staff/superuser only |
| `can_update_profile` | user, business | Delegates to `can_update` |
| `can_view_profile` | user, business, profile | Delegates to `can_view` + profile visibility check |

**PlatformPolicy** — Location: `apps/organization/platform/policies.py`

| Method | Args | Behavior |
|--------|------|----------|
| `can_configure` | user | Superuser only |
| `can_update_settings` | user | Superuser only |
| `can_update_profile` | user | Staff/superuser |
| `can_view` | user | Any authenticated user |

---

## 5. API Layer

### 5.1 Business Endpoints

Base path: `/api/v1/business/`

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/` | GET | BusinessListCreateView | IsAuthenticated | List active businesses (paginated) |
| `/` | POST | BusinessListCreateView | IsAuthenticated + Policy | Create new business |
| `/my/` | GET | MyBusinessListView | IsAuthenticated | List current user's businesses |
| `/id/<uuid>/` | GET | BusinessByIdView | IsAuthenticated + Policy | Get business by UUID |
| `/<slug>/` | GET | BusinessDetailView | IsAuthenticated + Policy | Get business by slug (301 redirect if slug changed) |
| `/<slug>/` | PATCH | BusinessDetailView | IsAuthenticated + Policy | Update business |
| `/<slug>/` | DELETE | BusinessDetailView | IsAuthenticated + Policy | Soft delete business |
| `/<slug>/slug/` | PATCH | BusinessSlugUpdateView | IsAuthenticated + Policy | Change business slug |
| `/<slug>/profile/` | GET | BusinessProfileView | IsAuthenticated + Policy | Get business profile |
| `/<slug>/profile/` | PATCH | BusinessProfileView | IsAuthenticated + Policy | Update business profile |
| `/<slug>/suspend/` | POST | BusinessSuspendView | IsAuthenticated + Staff | Suspend business |
| `/<slug>/reactivate/` | POST | BusinessReactivateView | IsAuthenticated + Staff | Reactivate business |
| `/<slug>/archive/` | POST | BusinessArchiveView | IsAuthenticated + Policy | Archive business |

Plus RBAC delegation routes: `roles/`, `members/` under business slug (from `apps.rbac.urls`).

### 5.2 Platform Endpoints

Base path: `/api/v1/platform/`

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/account/` | GET | PlatformAccountView | IsAuthenticated | Get platform account |
| `/account/` | POST | PlatformAccountView | IsAuthenticated + Superuser | Configure platform (one-time) |
| `/profile/` | GET | PlatformProfileView | IsAuthenticated | Get platform profile |
| `/profile/` | PATCH | PlatformProfileView | IsAuthenticated + Staff | Update platform profile |
| `/settings/` | PATCH | PlatformSettingsView | IsAuthenticated + Superuser | Update platform settings |

Plus RBAC delegation routes: `roles/`, `members/` under platform (from `apps.rbac.urls`).

### 5.3 Serializers

**Business Input Serializers** — Location: `apps/organization/business/serializers.py`

| Serializer | Type | Key Fields | Notes |
|------------|------|------------|-------|
| BusinessCreateInput | Input | legal_name, country, slug?, business_type? | Slug auto-generated from legal_name if omitted |
| BusinessUpdateInput | Input | legal_name?, registration_number?, tax_id?, country?, legal_address?, business_type? | All fields optional |
| BusinessSlugUpdateInput | Input | slug | New slug value |
| BusinessSuspendInput | Input | reason | Suspension reason |

**Business Output Serializers** — Location: `apps/organization/business/serializers.py`

| Serializer | Type | Key Fields | Notes |
|------------|------|------------|-------|
| BusinessAccountOutput | Output | All fields + nested profile | Full detail view |
| BusinessAccountListOutput | Output | id, slug, legal_name, status, country | Compact list view |
| BusinessAccountMinimalOutput | Output | id, slug, legal_name | Minimal reference |
| BusinessProfileOutput | Output | All profile fields | Profile detail view |

**Platform Input Serializers** — Location: `apps/organization/platform/serializers.py`

| Serializer | Type | Key Fields | Notes |
|------------|------|------------|-------|
| PlatformConfigureInput | Input | name, settings? | One-time configuration |
| PlatformSettingsUpdateInput | Input | settings | Merged into existing settings |
| PlatformProfileUpdateInput | Input | name?, tagline?, description?, logo?, favicon?, primary_color?, secondary_color?, contact_email?, contact_phone?, address?, social_links? | All fields optional |

**Platform Output Serializers** — Location: `apps/organization/platform/serializers.py`

| Serializer | Type | Key Fields | Notes |
|------------|------|------------|-------|
| PlatformAccountOutput | Output | All fields + nested profile | Full detail view |
| PlatformAccountMinimalOutput | Output | id, is_configured | Minimal reference |
| PlatformProfileOutput | Output | All profile fields | Profile detail view |

---

## 6. Types & Constants

### Enums

Location: `apps/core/constants.py`

| Enum | Values |
|------|--------|
| `AccountType` | PLATFORM, BUSINESS |
| `BusinessType` | SOLE_PROPRIETORSHIP, PARTNERSHIP, LLC, CORPORATION, NONPROFIT, COOPERATIVE, OTHER |
| `BusinessStatus` | PENDING, ACTIVE, SUSPENDED, ARCHIVED, DELETED |
| `VerificationStatus` | UNVERIFIED, PENDING, VERIFIED, REJECTED, EXPIRED |
| `CompanySize` | 1, 2-10, 11-50, 51-200, 201-500, 500+ |
| `OwnerType` | SYSTEM, PLATFORM, BUSINESS |

### Business Status Transitions

```
PENDING → ACTIVE (implicit on creation / reactivation)
ACTIVE → SUSPENDED (staff action)
ACTIVE → ARCHIVED (owner action)
ACTIVE → DELETED (soft-delete)
SUSPENDED → ACTIVE (staff reactivation)
ARCHIVED → ACTIVE (reactivation)
```

### Verification Status Transitions

```
UNVERIFIED → PENDING (verification request submitted via Transaction system)
PENDING → VERIFIED (approved by platform authority)
PENDING → REJECTED (denied by platform authority)
VERIFIED → EXPIRED (future: re-verification required)
```

---

## 7. Key Flows

### Flow 1: Create Business Account

1. User POSTs to `/api/v1/business/` with `legal_name`, `country`, optional `slug` and `business_type`
2. `BusinessPolicy.can_create()` — any authenticated user passes
3. `BusinessAccountService.create_business()`:
   - Auto-generates slug from `legal_name` if not provided
   - Creates `BusinessAccount` (status=PENDING)
   - Creates `BusinessProfile` (display_name=legal_name)
   - Calls `RBACService.initialize_business_account()` to set up owner role and membership
   - Audits `BUSINESS_CREATED`
4. Returns 201 with serialized business account and nested profile

### Flow 2: Slug Change with History

1. Owner PATCHes `/api/v1/business/<old-slug>/slug/` with `{ "slug": "new-slug" }`
2. `BusinessPolicy.can_update_slug()` — checks ownership (STUB: created_by)
3. `BusinessAccountService.update_slug()`:
   - Creates `BusinessSlugHistory` entry with `old_slug=<old-slug>`
   - Updates `business.slug` to `new-slug`
   - Audits `BUSINESS_SLUG_CHANGED`
4. Returns 200 with updated business

### Flow 3: Slug Redirect (301)

1. Client GETs `/api/v1/business/<old-slug>/`
2. `BusinessDetailView` calls `BusinessAccountSelector.get_by_slug_or_redirect()`
3. Selector queries `BusinessSlugHistory` for `old_slug` match
4. If found: returns the business and the current slug
5. View returns **301 redirect** to `/api/v1/business/<current-slug>/`

### Flow 4: Business Verification (via Transaction System)

1. Business owner creates a `business_verification_request` via the Transaction API
2. Platform authority reviews and accepts the transaction
3. Transaction system's `VerificationOutcomeHandler.handle_accepted()` calls:
   - `BusinessAccountService.update_verification_status(business, VERIFIED, actor)`
4. Business's `verification_status` updated to `VERIFIED`, `verified_at` and `verified_by` set
5. Audits `VERIFICATION_APPROVED`

### Flow 5: Platform Configuration (One-Time)

1. Superuser POSTs to `/api/v1/platform/account/` with `{ "name": "...", "settings": {...} }`
2. `PlatformPolicy.can_configure()` — superuser only
3. `PlatformAccountService.configure()`:
   - Updates singleton PlatformAccount: sets `is_configured=True`, stores settings
   - Creates or updates PlatformProfile with provided name
   - Calls `RBACService.initialize_platform_account()` to set up platform roles
   - Audits `PLATFORM_CONFIGURED`
4. Returns 201 with platform account and nested profile
5. Subsequent POST attempts are rejected (already configured)

---

## 8. Permissions & Authorization

### Business Policy Rules

| Action | Who Can Perform | Implementation |
|--------|----------------|----------------|
| Create business | Any authenticated user | `BusinessPolicy.can_create()` |
| View business | Staff OR business is active | `BusinessPolicy.can_view()` |
| Update business | **STUB**: Staff OR `created_by` | `BusinessPolicy.can_update()` |
| Change slug | **STUB**: `created_by` only | `BusinessPolicy.can_update_slug()` |
| Delete business | **STUB**: Superuser OR `created_by` | `BusinessPolicy.can_delete()` |
| Archive business | **STUB**: `created_by` only | `BusinessPolicy.can_archive()` |
| Suspend business | Staff/superuser | `BusinessPolicy.can_suspend()` |
| Reactivate business | Staff/superuser | `BusinessPolicy.can_reactivate()` |
| Verify business | Staff/superuser | `BusinessPolicy.can_verify()` |
| Update profile | Delegates to `can_update` | `BusinessPolicy.can_update_profile()` |
| View profile | `can_view` + profile visibility | `BusinessPolicy.can_view_profile()` |

### Platform Policy Rules

| Action | Who Can Perform | Implementation |
|--------|----------------|----------------|
| Configure platform | Superuser only | `PlatformPolicy.can_configure()` |
| Update settings | Superuser only | `PlatformPolicy.can_update_settings()` |
| Update profile | Staff/superuser | `PlatformPolicy.can_update_profile()` |
| View platform | Any authenticated user | `PlatformPolicy.can_view()` |

### Audit Actions (14)

| Action | Constant | Triggered By |
|--------|----------|--------------|
| Platform Configured | `org.platform.configured` | `PlatformAccountService.configure` |
| Platform Settings Updated | `org.platform.settings_updated` | `PlatformAccountService.update_settings` |
| Platform Profile Updated | `org.platform.profile_updated` | `PlatformProfileService.update` |
| Business Created | `org.business.created` | `BusinessAccountService.create_business` |
| Business Updated | `org.business.updated` | `BusinessAccountService.update` |
| Business Suspended | `org.business.suspended` | `BusinessAccountService.suspend` |
| Business Reactivated | `org.business.reactivated` | `BusinessAccountService.reactivate` |
| Business Archived | `org.business.archived` | `BusinessAccountService.archive` |
| Business Deleted | `org.business.deleted` | `BusinessAccountService.soft_delete` |
| Business Slug Changed | `org.business.slug_changed` | `BusinessAccountService.update_slug` |
| Business Profile Updated | `org.business.profile_updated` | `BusinessProfileService.update` |
| Verification Approved | `org.verification.approved` | `BusinessAccountService.update_verification_status` |
| Verification Rejected | `org.verification.rejected` | `BusinessAccountService.update_verification_status` |
| Ownership Transfer Initiated | `org.ownership.transfer_initiated` | (Reserved for Transaction system) |

---

## 9. Configuration & Gotchas

### RBAC Integration Points

| Integration | Service Method | RBAC Call |
|------------|---------------|-----------|
| Business creation | `BusinessAccountService.create_business()` | `RBACService.initialize_business_account(business, owner)` |
| Platform configuration | `PlatformAccountService.configure()` | `RBACService.initialize_platform_account(platform, actor)` |
| Business verification | Transaction system outcome handler | `BusinessAccountService.update_verification_status()` |

### Gotchas

- **STUB policies**: BusinessPolicy methods (`can_update`, `can_update_slug`, `can_delete`, `can_archive`) use `created_by` checks as placeholders. These will be replaced with RBAC membership checks when integration is complete.
- **STUB selectors**: `list_by_owner()` and `list_by_member()` both filter by `created_by` instead of querying RBAC memberships. Results will be incorrect for businesses where ownership has been transferred.
- **Singleton enforcement**: PlatformAccount uses both a `unique` constraint on `singleton_key` and a `CheckConstraint` ensuring `singleton_key=1`. The `save()` override always resets `singleton_key` to 1. Do not attempt to create additional PlatformAccount rows.
- **Data migration ordering**: `0002_create_platform_singleton` creates the singleton row. If this migration runs before RBAC migrations, `initialize_platform_account()` may fail. Ensure RBAC migrations are applied first.
- **Slug uniqueness spans history**: `slug_exists()` checks both `BusinessAccount.slug` and `BusinessSlugHistory.old_slug`. A slug rejected by history can never be reused by any business.
- **soft_delete() field saving order**: `soft_delete()` only saves `is_deleted`, `deleted_at`, `deleted_by`. Any other field changes (e.g., `status=DELETED`) must be saved BEFORE calling `soft_delete()`.
- **auto_now_add fields**: `created_at` cannot be set at creation time. Use `Model.objects.filter(id=obj.id).update(created_at=...)` after factory creation when testing time-dependent behavior.
- **No image processing**: Logo and cover images are stored as-is with no resizing, compression, or format validation beyond Django's ImageField checks.

---

## 10. Local Development

### Setup

```bash
# Already included in INSTALLED_APPS
# Run migrations
cd backend
python manage.py migrate

# Verify models
python manage.py shell -c "from apps.organization.business.models import BusinessAccount, BusinessProfile, BusinessSlugHistory; print('Business OK')"
python manage.py shell -c "from apps.organization.platform.models import PlatformAccount, PlatformProfile; print('Platform OK')"

# Verify singleton exists
python manage.py shell -c "from apps.organization.platform.selectors import PlatformAccountSelector; print(PlatformAccountSelector.exists())"
```

### Test Data

- `BusinessAccountFactory` / `BusinessProfileFactory` — configurable factories in `apps/organization/tests/factories.py`
- `PlatformAccountFactory` / `PlatformProfileFactory` — platform factories (singleton-aware)
- Fixtures in `apps/organization/tests/conftest.py`: business, platform, user, staff_user, superuser
- Canonical `UserFactory` from `apps/users/tests/factories.py` (single source of truth)

### Useful URLs

| URL | Method | Purpose |
|-----|--------|---------|
| `/api/v1/business/` | GET | List active businesses |
| `/api/v1/business/` | POST | Create a new business |
| `/api/v1/business/my/` | GET | List current user's businesses |
| `/api/v1/business/<slug>/` | GET | View business detail |
| `/api/v1/platform/account/` | GET | View platform account |
| `/api/v1/platform/profile/` | GET | View platform profile |

---

## 11. Deployment

| Aspect | Local (SQLite) | Production (PostgreSQL + Redis) |
|--------|----------------|-------------------------------|
| Database | SQLite | PostgreSQL |
| Cache | DummyCache | Redis |
| Singleton | Enforced via CheckConstraint | Enforced via CheckConstraint |
| Image Storage | Local filesystem | S3 via AWS_* settings |
| RBAC Init | Sync in-process | Sync in-process |

### Pre-Deploy Checklist

- [ ] Run migrations: `python manage.py migrate`
- [ ] Verify platform singleton exists: `python manage.py shell -c "from apps.organization.platform.selectors import PlatformAccountSelector; print(PlatformAccountSelector.exists())"`
- [ ] Verify RBAC roles are seeded for platform account
- [ ] Verify S3 bucket configured for image uploads (logo, cover, favicon)
- [ ] Configure platform via superuser POST to `/api/v1/platform/account/`

---

## 12. Testing

| Module | Tests | Status |
|--------|-------|--------|
| business/test_models.py | 17 | Pass |
| business/test_services.py | 21 | Pass |
| business/test_views.py | 25 | Pass |
| platform/test_models.py | 11 | Pass |
| platform/test_services.py | 11 | Pass |
| platform/test_views.py | 13 | Pass |
| **Total** | **98** | **Pass** |

**Test breakdown by class:**

| Test Class | Count | File |
|------------|-------|------|
| TestBusinessAccountModel | 9 | business/test_models.py |
| TestBusinessProfileModel | 5 | business/test_models.py |
| TestBusinessSlugHistoryModel | 3 | business/test_models.py |
| TestBusinessAccountService | 17 | business/test_services.py |
| TestBusinessProfileService | 4 | business/test_services.py |
| TestBusinessListCreateView | 5 | business/test_views.py |
| TestMyBusinessListView | 2 | business/test_views.py |
| TestBusinessDetailView | 7 | business/test_views.py |
| TestBusinessSlugUpdateView | 2 | business/test_views.py |
| TestBusinessProfileView | 3 | business/test_views.py |
| TestBusinessSuspendView | 2 | business/test_views.py |
| TestBusinessReactivateView | 2 | business/test_views.py |
| TestBusinessArchiveView | 2 | business/test_views.py |
| TestPlatformAccountModel | 5 | platform/test_models.py |
| TestPlatformProfileModel | 6 | platform/test_models.py |
| TestPlatformAccountService | 5 | platform/test_services.py |
| TestPlatformProfileService | 6 | platform/test_services.py |
| TestPlatformAccountView | 5 | platform/test_views.py |
| TestPlatformProfileView | 4 | platform/test_views.py |
| TestPlatformSettingsView | 4 | platform/test_views.py |

**Test infrastructure:**
- `apps/organization/tests/factories.py` — BusinessAccountFactory, BusinessProfileFactory, PlatformAccountFactory, PlatformProfileFactory
- `apps/organization/tests/conftest.py` — Shared fixtures (users, accounts, profiles)
- All tests use `@pytest.mark.django_db`, AAA pattern, factory-boy

---

## 13. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/organization/__init__.py` | Package init |
| `apps/organization/apps.py` | Django app config |
| `apps/organization/admin.py` | Top-level admin registration |
| `apps/organization/business/__init__.py` | Business subpackage init |
| `apps/organization/business/models.py` | BusinessAccount, BusinessProfile, BusinessSlugHistory models |
| `apps/organization/business/selectors.py` | BusinessAccountSelector (10 methods), BusinessProfileSelector (2 methods) |
| `apps/organization/business/services.py` | BusinessAccountService (8 methods), BusinessProfileService (1 method) |
| `apps/organization/business/policies.py` | BusinessPolicy (11 authorization methods) |
| `apps/organization/business/serializers.py` | 4 input + 4 output serializers |
| `apps/organization/business/views.py` | 8 views (ListCreate, MyList, Detail, ById, SlugUpdate, Profile, Suspend, Reactivate, Archive) |
| `apps/organization/business/urls.py` | Business URL patterns |
| `apps/organization/business/admin.py` | Business admin registration |
| `apps/organization/platform/__init__.py` | Platform subpackage init |
| `apps/organization/platform/models.py` | PlatformAccount (singleton), PlatformProfile models |
| `apps/organization/platform/selectors.py` | PlatformAccountSelector (3 methods), PlatformProfileSelector (1 method) |
| `apps/organization/platform/services.py` | PlatformAccountService (2 methods), PlatformProfileService (1 method) |
| `apps/organization/platform/policies.py` | PlatformPolicy (4 authorization methods) |
| `apps/organization/platform/serializers.py` | 3 input + 3 output serializers |
| `apps/organization/platform/views.py` | 3 views (Account, Profile, Settings) |
| `apps/organization/platform/urls.py` | Platform URL patterns |
| `apps/organization/platform/admin.py` | Platform admin registration |
| `apps/organization/migrations/0001_initial.py` | Schema migration (5 tables) |
| `apps/organization/migrations/0002_create_platform_singleton.py` | Data migration (singleton creation) |
| `apps/organization/tests/__init__.py` | Test package init |
| `apps/organization/tests/conftest.py` | Shared test fixtures |
| `apps/organization/tests/factories.py` | 4 model factories |
| `apps/organization/tests/business/__init__.py` | Business test package init |
| `apps/organization/tests/business/test_models.py` | 17 tests (3 test classes) |
| `apps/organization/tests/business/test_services.py` | 21 tests (2 test classes) |
| `apps/organization/tests/business/test_views.py` | 25 tests (8 test classes) |
| `apps/organization/tests/platform/__init__.py` | Platform test package init |
| `apps/organization/tests/platform/test_models.py` | 11 tests (2 test classes) |
| `apps/organization/tests/platform/test_services.py` | 11 tests (2 test classes) |
| `apps/organization/tests/platform/test_views.py` | 13 tests (3 test classes) |

---

## 14. Known Limitations

1. **STUB authorization policies**: BusinessPolicy uses `created_by` checks instead of RBAC membership queries for `can_update`, `can_update_slug`, `can_delete`, `can_archive` — will be updated when RBAC integration is wired
2. **STUB selectors**: `list_by_owner()` and `list_by_member()` filter by `created_by` instead of querying RBAC memberships via `MembershipSelector`
3. **No image processing**: Logo and cover images are uploaded and stored as-is with no resizing, compression, or format conversion
4. **No slug redirect middleware**: Slug redirects (301) only happen within `BusinessDetailView`; direct API calls to other endpoints with old slugs will return 404
5. **No business search/filtering**: List endpoint returns all active businesses with pagination but no search, filter, or sort parameters

---

## 15. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Wire BusinessPolicy to RBAC memberships | Replace `created_by` checks with membership-based authorization | P0 |
| Wire `list_by_owner`/`list_by_member` to MembershipSelector | Replace `created_by` filter with RBAC membership queries | P0 |
| Business search/filtering endpoint | Add search by name, filter by country/industry/status, sort options | P1 |
| Image processing pipeline | Resize, compress, and validate logos/covers on upload | P2 |
| Slug redirect middleware | Handle old slugs across all endpoints, not just BusinessDetailView | P2 |
| Business analytics dashboard | Activity metrics, member counts, verification status tracking | P3 |
| Multi-language business profiles | Support localized display_name, tagline, description | P3 |

---

## 16. Changelog

### v1 (2026-02-24)
- Initial implementation: dual account types (Platform singleton + Business multi-tenant)
- Subpackage architecture with independent models, selectors, services, policies, serializers, views per account type
- Slug history system with 301 redirect support and permanent uniqueness
- Platform singleton with CheckConstraint enforcement and one-time configuration flow
- Business verification integration via Transaction system's VerificationOutcomeHandler
- RBAC initialization hooks for both account types
- 14 audit actions across all organization operations
- 98 tests across 6 test files (17 model + 21 service + 25 view for business; 11 model + 11 service + 13 view for platform)
