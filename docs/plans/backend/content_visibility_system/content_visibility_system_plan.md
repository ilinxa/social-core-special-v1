# Content Visibility System + 3-Tier Profile Privacy

## Context

The platform needs a clean, scalable content visibility system BEFORE building content/component apps. Every content item falls into one of 3 tiers:

- **T1 (ALWAYS_PUBLIC)**: System-enforced. Always visible to anyone who can discover the entity. Not configurable.
- **T2 (CONDITIONAL)**: User-configurable visibility per field. Account owner (or member with permission) sets who can see each T2 item. Members bypass T2 rules entirely (their access is RBAC-controlled).
- **T3 (ALWAYS_PRIVATE)**: System-enforced. Hidden from non-members. Within members, further gated by RBAC permissions.

The `is_public` flag controls **discoverability** AND acts as a **global T2 override** — when `is_public=True`, all T2 content is visible to everyone.

---

## Visibility Level Hierarchies

Each account type has different relationship levels (no separate PRIVATE level — members is the lowest):

```
User:       CONNECTIONS (0) → WORLD (1)

Business:   MEMBERS (0) → CONNECTIONS (1) → FOLLOWERS (2) → WORLD (3)

Platform:   MEMBERS (0) → WORLD (1)
```

**Access rules per tier:**

| Tier | Owner/Self | Member | Non-Member (follower/conn/world) |
|------|-----------|--------|----------------------------------|
| T1 | Always visible | Always visible | Always visible |
| T2 | Always visible | Always visible (bypass) | Check `is_public` → if True, visible. If False, check per-field level |
| T3 | Always visible | Check RBAC permission | Never visible |

---

## Field Classification

### User

| Tier | Fields |
|------|--------|
| T1 | first_name, last_name, full_name, display_name, avatar_url, has_avatar, cover_image_url, has_cover_image, bio, country, city, tags, is_public |
| T2 | *(none currently — future components)* |
| T3 | phone, timezone, language *(+ email on User model)* |

### Business Account

| Tier | Account Fields | Profile Fields |
|------|---------------|----------------|
| T1 | id, slug, legal_name, country, city, business_type, status, verification_status, verified_at, is_platform_branch, open_member_request, created_at, updated_at | display_name, tagline, description, logo, cover_image, website, industry, company_size, founded_year, social_links, tags, is_public, created_at, updated_at |
| T2 | — | contact_email (default: FOLLOWERS), contact_phone (default: FOLLOWERS) |
| T3 | registration_number (`can_view_legal_info`), tax_id (`can_view_legal_info`), legal_address (`can_view_legal_info`), settings (`can_edit_business`), max_members (`can_manage_members`) | — |

### Platform

| Tier | Fields |
|------|--------|
| T1 | All current fields (platform is fully public) |
| T2 | *(none currently)* |
| T3 | *(none currently)* |

---

## Architecture

### New Files

```
backend/apps/core/visibility/
    __init__.py          # Re-exports
    enums.py             # ContentTier, UserVisibility, BusinessVisibility, PlatformVisibility
    registry.py          # FieldVisibilityConfig + per-account-type field registries
    resolver.py          # VisibilityResolver + ViewerAccess dataclass
    serializers.py       # VisibilityAwareSerializerMixin + VisibilityOverrideInput
```

### Modified Files

| File | Change |
|------|--------|
| `apps/users/models.py` | Add `visibility_overrides` JSONField to UserProfile |
| `apps/organization/business/models.py` | Add `visibility_overrides` JSONField to BusinessProfile |
| `apps/organization/platform/models.py` | Add `visibility_overrides` JSONField to PlatformProfile |
| `apps/organization/business/serializers.py` | Add `VisibilityAwareSerializerMixin` to `BusinessProfileOutput` + `BusinessAccountOutput` |
| `apps/users/serializers.py` | Expand `UserLimitedOutput` to include T1 fields; add `VisibilityAwareSerializerMixin` to profile serializers |
| `apps/organization/business/views.py` | Pass visibility context to serializers in `BusinessDetailView` + `BusinessByIdView` |
| `apps/users/views.py` | Always inject `_permissions`/`_relationship` for limited views; pass visibility context |
| `apps/users/policies.py` | Add connection check to `can_view_profile()` |
| `apps/organization/business/policies.py` | Add follower check to `can_view_profile()` |
| `apps/explore/selectors.py` | Add `include_private` param to `search_businesses()`; remove `is_public` filter from `search_users()` |
| `apps/explore/serializers.py` | Remove `email` from `ExploreUserOutput`; add `is_public` to explore outputs |
| `apps/explore/views.py` | Pass `include_private` based on auth |
| `apps/rbac/permissions/registry.py` | Add `can_view_legal_info` permission |
| `apps/rbac/migrations/0009_seed_visibility_permissions.py` | Data migration for new permission |

---

## Phase 1: Visibility Infrastructure

### 1a. Enums (`apps/core/visibility/enums.py`)

```python
class ContentTier(models.TextChoices):
    ALWAYS_PUBLIC = "T1", "Always Public"
    CONDITIONAL = "T2", "Conditional"
    ALWAYS_PRIVATE = "T3", "Always Private"

class UserVisibility(models.IntegerChoices):
    CONNECTIONS = 0, "Connections"
    WORLD = 1, "All authenticated users"

class BusinessVisibility(models.IntegerChoices):
    MEMBERS = 0, "Members"
    CONNECTIONS = 1, "Connected accounts"
    FOLLOWERS = 2, "Followers"
    WORLD = 3, "World (everyone)"

class PlatformVisibility(models.IntegerChoices):
    MEMBERS = 0, "Platform members"
    WORLD = 1, "World (everyone)"
```

### 1b. Registry (`apps/core/visibility/registry.py`)

```python
@dataclass(frozen=True)
class FieldVisibilityConfig:
    tier: ContentTier
    default_level: int | None = None        # Only for T2
    required_permission: str | None = None  # Only for T3 (RBAC gate within members)
```

Four registries: `USER_PROFILE_FIELDS`, `BUSINESS_ACCOUNT_FIELDS`, `BUSINESS_PROFILE_FIELDS`, `PLATFORM_PROFILE_FIELDS`. Plus lookup helpers: `get_registry()`, `get_t2_fields()`, `get_visibility_choices()`.

### 1c. ViewerAccess Dataclass + Resolver (`apps/core/visibility/resolver.py`)

```python
@dataclass(frozen=True)
class ViewerAccess:
    level: int               # Relationship level (from VisibilityLevel enum)
    is_member: bool          # Whether viewer is a member of the account
    is_owner_or_self: bool   # Owner/self bypass
    permissions: frozenset   # RBAC permission codes (for T3 checks)
```

**`VisibilityResolver` methods:**

| Method | Purpose | DB Queries |
|--------|---------|-----------|
| `compute_viewer_access(viewer, account_type, account_id)` → `ViewerAccess` | Compute once per request | 1-3 (membership, follow, connection) — short-circuits |
| `filter_fields(data, account_type, viewer_access, visibility_overrides, is_public)` → `dict` | Filter serialized data | 0 (pure logic) |
| `can_see_field(field_name, account_type, viewer_access, ...)` → `bool` | Single field check | 0 |
| `get_visibility_settings(account_type, visibility_overrides)` → `list[dict]` | For owner settings UI | 0 |

**Filter logic per tier:**

```python
T1 → always include
T2 → include if:
    - viewer is owner/self, OR
    - viewer is member (bypass), OR
    - is_public=True (global override), OR
    - viewer_access.level >= required_level
T3 → include if:
    - viewer is owner/self, OR
    - viewer is member AND (no required_permission OR permission in viewer_access.permissions)
```

**`compute_viewer_access()` logic for Business:**
```
staff/superuser → level=WORLD+1, is_member=True, is_owner=True
owner → level=WORLD+1, is_member=True, is_owner=True
member → level=WORLD+1, is_member=True, permissions=from_rbac
follower → level=FOLLOWERS
B2B connected → level=CONNECTIONS
authenticated → level=WORLD
anonymous → level=WORLD (but T2 only visible if is_public=True)
```

Note: Members get `level=WORLD+1` (above max) because they bypass T2 checks. Their T3 access is via `permissions`.

### 1d. Serializer Mixin (`apps/core/visibility/serializers.py`)

```python
class VisibilityAwareSerializerMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        visibility_ctx = self.context.get('visibility')
        if visibility_ctx is None:
            return data  # Backward compatible
        return VisibilityResolver.filter_fields(
            data=data,
            account_type=visibility_ctx['account_type'],
            viewer_access=visibility_ctx['viewer_access'],
            visibility_overrides=visibility_ctx.get('visibility_overrides'),
            is_public=visibility_ctx.get('is_public', True),
        )
```

DRF propagates `context` to nested serializers automatically — so passing `visibility` context to the parent serializer flows to nested profile serializers.

---

## Phase 2: Model Changes + Migration

Add `visibility_overrides = models.JSONField(default=dict, blank=True)` to:
- `UserProfile` → migration `0011_userprofile_visibility_overrides.py`
- `BusinessProfile` + `PlatformProfile` → migration `0006_add_visibility_overrides.py`

Add `can_view_legal_info` RBAC permission:
- `apps/rbac/permissions/registry.py` — add to PERMISSIONS list
- `apps/rbac/migrations/0009_seed_visibility_permissions.py` — data migration

---

## Phase 3: Apply to User Profiles

### 3a. Policy: Add connection check
**File**: `apps/users/policies.py` — `can_view_profile()` line 37:
```python
# After is_public check fails, add:
from apps.network.selectors import ConnectionSelector
if ConnectionSelector.is_connected(user_a_id=viewer.id, user_b_id=target.id):
    return True
return False
```

### 3b. Serializer: Expand `UserLimitedOutput`
**File**: `apps/users/serializers.py` — Replace hand-built `get_profile()` with nested `UserPublicProfileOutput` (reuses existing serializer that excludes T3 fields).

### 3c. View: Always inject `_permissions` + `_relationship`
**File**: `apps/users/views.py` — `UserPublicDetailView.get()`:
- Set `_inject_permissions = True` and `_inject_relationship = True` BEFORE the serializer branch
- Both limited and full responses get `_permissions` + `_relationship`

---

## Phase 4: Apply to Business Profiles

### 4a. Policy: Add follower check
**File**: `apps/organization/business/policies.py` — `can_view_profile()` line 247: add `FollowSelector.is_following()` check after member check.

### 4b. Serializer: Apply mixin
**File**: `apps/organization/business/serializers.py`:
- Add `VisibilityAwareSerializerMixin` to `BusinessProfileOutput` and `BusinessAccountOutput`
- The mixin handles T2 filtering (contact_email, contact_phone) and T3 filtering (registration_number, tax_id, etc.)
- No separate `BusinessAccountLimitedOutput` needed — the mixin dynamically filters based on viewer access

### 4c. Views: Pass visibility context
**File**: `apps/organization/business/views.py` — `BusinessDetailView.get()` and `BusinessByIdView.get()`:
```python
viewer_access = VisibilityResolver.compute_viewer_access(
    viewer=request.user, account_type="business", account_id=business.id,
)
serializer = BusinessAccountOutput(business, context={
    'request': request,
    'visibility': {
        'account_type': 'business',
        'viewer_access': viewer_access,
        'visibility_overrides': business.profile.visibility_overrides,
        'is_public': business.profile.is_public,
    },
})
```

Add `is_limited` to response when viewer cannot see full profile (non-member, non-follower, private profile):
```python
response_data = serializer.data
if not viewer_access.is_member and not business.profile.is_public:
    response_data['is_limited'] = True
```

---

## Phase 5: Apply to Explore

### 5a. Selectors
**File**: `apps/explore/selectors.py`:
- `search_businesses()`: Add `include_private: bool = False` param. Move `profile__is_public=True` to conditional filter.
- `search_users()`: Remove `profile__is_public=True` filter (auth-gated by view).

### 5b. Serializers
**File**: `apps/explore/serializers.py`:
- Remove `email` from `ExploreUserOutput.Meta.fields` (T3 bug fix)
- Add `is_public` to `ExploreUserProfileOutput` and `ExploreBusinessProfileOutput` fields

### 5c. Views
**File**: `apps/explore/views.py`:
- `ExploreBusinessSearchView.get()`: Pass `include_private=request.user.is_authenticated`
- `ExploreCombinedView.get()`: Same for business section

---

## Phase 6: Visibility Settings API

### Endpoints (for account owners to configure T2 field visibility)

```
GET  /api/v1/business/{slug}/profile/visibility/    → list T2 fields with current levels + choices
PATCH /api/v1/business/{slug}/profile/visibility/   → update overrides

GET  /api/v1/users/me/profile/visibility/           → (empty for now, future-ready)
PATCH /api/v1/users/me/profile/visibility/          → (empty for now, future-ready)
```

**GET response:**
```json
[
  {
    "field_name": "contact_email",
    "current_level": 2,
    "default_level": 2,
    "choices": [
      {"value": 0, "label": "Members"},
      {"value": 1, "label": "Connected accounts"},
      {"value": 2, "label": "Followers"},
      {"value": 3, "label": "World (everyone)"}
    ]
  }
]
```

**PATCH body:** `{"overrides": {"contact_email": 3}}`

Permission: account owner OR member with `can_edit_profile` permission.

---

## Phase 7: Tests (~78 tests)

| File | Count | Coverage |
|------|-------|---------|
| `apps/core/tests/test_visibility_enums.py` | ~8 | Enum ordering, hierarchy, labels |
| `apps/core/tests/test_visibility_registry.py` | ~12 | Config validation, registry lookups, T2 field queries |
| `apps/core/tests/test_visibility_resolver.py` | ~25 | compute_viewer_access (all account types x all relationships), filter_fields (T1/T2/T3 x member/non-member x public/private), RBAC-gated T3 |
| `apps/core/tests/test_visibility_serializers.py` | ~8 | Mixin filtering, backward compat, input validation |
| User policy + view tests | ~8 | Connection-based access, limited with T1 fields, always inject _permissions/_relationship |
| Business policy + view tests | ~10 | Follower-based access, T2 filtering, T3 hidden, is_limited flag |
| Explore tests | ~7 | Private entity discovery, email removal, is_public in output |
| **Total** | **~78** | |

---

## Implementation Order

1. `apps/core/visibility/__init__.py`, `enums.py`, `registry.py` — foundation
2. `apps/core/visibility/resolver.py` — ViewerAccess + VisibilityResolver
3. `apps/core/visibility/serializers.py` — mixin + input/output
4. Profile model migrations (`visibility_overrides` JSONField)
5. RBAC migration (`can_view_legal_info` permission)
6. User policy + serializer + view changes (Phase 3)
7. Business policy + serializer + view changes (Phase 4)
8. Explore changes (Phase 5)
9. Visibility settings endpoints (Phase 6)
10. Tests (Phase 7)
11. Progress entry

---

## Verification

1. Unit tests: `pytest apps/core/tests/test_visibility*.py -v`
2. Existing tests: `pytest -o 'DJANGO_SETTINGS_MODULE=backend_core.settings.local'` — all 3400+ pass
3. Manual smoke:
   - Anonymous views public business → sees all T1 + T2 fields
   - Anonymous views private business → 403
   - Authenticated non-follower views private business → sees T1 only, `is_limited: true`
   - Follower views private business → sees T1 + T2 (contact info)
   - Member views any business → sees T1 + T2 + T3 (based on RBAC permission)
   - Owner views own business → sees everything
   - Private user, non-connected → limited profile with T1 fields + `_permissions` + `_relationship`
   - Private user, connected → full profile
