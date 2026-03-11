# Permission-Aware API Responses (Tier 1.5) — Implementation Reference

**Version:** v1
**Last Updated:** 2026-03-02
**Status:** Implemented

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Three-Tier Authorization                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tier 1: Membership Store (Zustand)                              │
│  ├── Nav sidebar filtering (useFilteredNav)                      │
│  ├── Route guards (BusinessGuard, PlatformGuard)                 │
│  └── Page-level action hints on list pages                       │
│                                                                  │
│  Tier 1.5: Response Permissions (THIS SYSTEM) ◄── NEW           │
│  ├── _permissions dict in GET detail responses                   │
│  ├── In-page UI gating (edit buttons, panels, danger zones)      │
│  └── Resource-specific, RBAC-evaluated booleans                  │
│                                                                  │
│  Tier 3: Backend Enforcement (existing)                          │
│  ├── Policy checks on POST/PATCH/DELETE                          │
│  └── Returns 403 PermissionDenied if unauthorized                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Backend Data Flow:
┌────────────┐   ┌───────────────────────┐   ┌──────────────────┐
│   APIView  │──▶│ PermissionInjectMixin │──▶│    Policy class   │
│   .get()   │   │ .finalize_response()  │   │ .get_viewer_     │
│            │   │                       │   │  permissions()    │
│ sets flag: │   │ checks:               │   │                  │
│ _inject_   │   │ • _inject_permissions  │   │ checks RBAC:     │
│ permissions│   │ • method == GET        │   │ • membership     │
│ = True     │   │ • policy_class exists  │   │ • role           │
│            │   │ • data is dict         │   │ • permissions    │
└────────────┘   └───────────────────────┘   └──────────────────┘
                         │                           │
                         ▼                           ▼
                  response.data["_permissions"] = {can_edit: true, ...}

Frontend Data Flow:
┌───────────────┐   ┌───────────────────┐   ┌──────────────────┐
│ fetchBusiness │──▶│ TanStack Query    │──▶│  Page Component  │
│ Api(slug)     │   │ useBusiness(slug) │   │                  │
│               │   │                   │   │  <Can allowed=   │
│ returns:      │   │ data includes     │   │   {perms.can_x}> │
│ Business +    │   │ _permissions      │   │    <EditBtn />   │
│ _permissions  │   │                   │   │  </Can>          │
└───────────────┘   └───────────────────┘   └──────────────────┘
```

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Injection mechanism | DRF `finalize_response()` hook | Runs after serialization, before network. No serializer changes needed |
| Opt-in flag | Explicit `self._inject_permissions = True` | Prevents accidental injection into list/paginated/error/redirect responses. Explicit > implicit |
| GET only | `request.method == "GET"` check in mixin | Mutation responses (POST/PATCH/DELETE) don't need permissions — the action already happened |
| Policy method | `get_viewer_permissions(**kwargs)` → `dict[str, bool]` | Each policy defines its own permission shape. No shared schema enforced |
| Two policy signatures | `(user, resource)` vs `(actor_context, resource)` | BusinessPolicy/PlatformPolicy resolve membership internally; FormTemplatePolicy uses pre-resolved ActorContext (more efficient for multi-check views) |
| Exception wrapping | `_safe_check()` for FormTemplatePolicy | FormTemplatePolicy raises `PermissionDenied` instead of returning bool. Wrapper converts exceptions to `False` |
| Platform RBAC | Refactored from staff-only to RBAC + staff bypass | Console UI must be purely RBAC-driven. `is_staff`/`is_superuser` are for Django admin panel only |
| Frontend type strategy | `type` alias, not `interface` | TypeScript `interface` doesn't satisfy `Record<string, boolean>` constraint used in `WithPermissions<T>` |

## 3. Backend — Mixin

### 3.1 PermissionInjectMixin

Location: `backend/apps/core/views.py`

```python
class PermissionInjectMixin:
    policy_class = None           # Set to e.g. BusinessPolicy
    _inject_permissions = False   # Set True in get() to opt in

    def _build_policy_kwargs(self) -> dict:
        raise NotImplementedError  # Override per view

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if (
            self._inject_permissions
            and request.method == "GET"
            and self.policy_class is not None
            and hasattr(response, "data")
            and isinstance(response.data, dict)
        ):
            response.data["_permissions"] = (
                self.policy_class.get_viewer_permissions(
                    **self._build_policy_kwargs()
                )
            )
        return response
```

**Five safety guards:**
1. `self._inject_permissions` — explicit opt-in per request
2. `request.method == "GET"` — mutations excluded
3. `self.policy_class is not None` — no policy = no injection
4. `hasattr(response, "data")` — handles edge cases (streaming, etc.)
5. `isinstance(response.data, dict)` — excludes list/array responses

## 4. Backend — Policies

### 4.1 BusinessPolicy.get_viewer_permissions

Location: `backend/apps/organization/business/policies.py:198`

| Key | Policy Method | Signature |
|-----|---------------|-----------|
| `can_view` | `BusinessPolicy.can_view` | `(user, business)` → `bool` |
| `can_edit` | `BusinessPolicy.can_update` | `(user, business)` → `bool` |
| `can_edit_profile` | `BusinessPolicy.can_update_profile` | `(user, business)` → `bool` |
| `can_delete` | `BusinessPolicy.can_delete` | `(user, business)` → `bool` |
| `can_change_slug` | `BusinessPolicy.can_update_slug` | `(user, business)` → `bool` |
| `can_archive` | `BusinessPolicy.can_archive` | `(user, business)` → `bool` |

**Permission matrix by role:**

| Permission | Owner | Member (no perms) | Member + `can_edit_business` | Non-member | Staff | Superuser |
|------------|-------|-------------------|-----------------------------|------------|-------|-----------|
| `can_view` | T | T | T | T | T | T |
| `can_edit` | T | F | T | F | T | T |
| `can_edit_profile` | T | F | F (needs `can_edit_profile`) | F | T | T |
| `can_delete` | T | F | F | F | F | T |
| `can_change_slug` | T | F | F | F | F | F |
| `can_archive` | T | F | F | F | F | F |

### 4.2 PlatformPolicy.get_viewer_permissions

Location: `backend/apps/organization/platform/policies.py:96`

| Key | Policy Method | Signature |
|-----|---------------|-----------|
| `can_view` | `PlatformPolicy.can_view` | `(user)` → `bool` |
| `can_edit_profile` | `PlatformPolicy.can_update_profile` | `(user)` → `bool` |
| `can_edit_settings` | `PlatformPolicy.can_update_settings` | `(user)` → `bool` |

**RBAC helper — `_has_platform_permission()`:**
```python
@staticmethod
def _has_platform_permission(*, user, permission_code: str) -> bool:
    platform = PlatformAccount.objects.first()
    if not platform:
        return False
    membership = MembershipSelector.get_active_membership_for_user_account(
        user=user, account_type=AccountType.PLATFORM, account_id=platform.id,
    )
    if not membership:
        return False
    permissions = PermissionSelector.get_permissions_for_membership(
        membership_id=membership.id,
    )
    return any(code == permission_code for code, scope in permissions)
```

**Permission matrix by role:**

| Permission | Platform Owner | Platform Admin | Global Moderator | Non-member | Staff | Superuser |
|------------|---------------|----------------|------------------|------------|-------|-----------|
| `can_view` | T | T | T | T (any authenticated) | T | T |
| `can_edit_profile` | T | T | F | F | T | T |
| `can_edit_settings` | T | T | F | F | F | T |

**Note:** Platform Admin gets `can_edit_profile` and `can_edit_settings` because migration `0005` adds `platform_only` to both `can_edit_profile` and `can_edit_business` applicable_scopes.

### 4.3 FormTemplatePolicy.get_viewer_permissions

Location: `backend/apps/forms/policies.py:108`

| Key | Policy Method | Signature |
|-----|---------------|-----------|
| `can_edit` | `FormTemplatePolicy.can_edit_form` | `(actor_context, form_template)` → raises or None |
| `can_delete` | `FormTemplatePolicy.can_delete_form` | `(actor_context, form_template)` → raises or None |
| `can_publish` | `FormTemplatePolicy.can_publish_form` | `(actor_context, form_template)` → raises or None |
| `can_archive` | `FormTemplatePolicy.can_archive_form` | `(actor_context, form_template)` → raises or None |

Uses `_safe_check()` wrapper (defined inline) to convert `PermissionDenied` exceptions into `False`. This handles resource-specific conditions like `is_system_form` (blocks all edits regardless of permissions).

**Not yet wired to views** — FormTemplateDetailView will integrate the mixin when the forms frontend is built.

## 5. Backend — View Wiring

### 5.1 Wired Views

| View | File | Line | policy_class | `_build_policy_kwargs()` |
|------|------|------|-------------|--------------------------|
| `BusinessByIdView` | `business/views.py` | ~191 | `BusinessPolicy` | `{"user": request.user, "business": self._resource}` |
| `BusinessDetailView` | `business/views.py` | ~245 | `BusinessPolicy` | `{"user": request.user, "business": self._resource}` |
| `BusinessProfileView` | `business/views.py` | ~461 | `BusinessPolicy` | `{"user": request.user, "business": self._resource}` |
| `PlatformAccountView` | `platform/views.py` | ~38 | `PlatformPolicy` | `{"user": request.user}` |
| `PlatformProfileView` | `platform/views.py` | ~138 | `PlatformPolicy` | `{"user": request.user}` |

### 5.2 Wiring Pattern

```python
class BusinessDetailView(PermissionInjectMixin, APIView):
    permission_classes = [IsAuthenticated]
    policy_class = BusinessPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "business": self._resource}

    def get(self, request, slug):
        business, redirect_slug = BusinessAccountSelector.get_by_slug_or_redirect(slug=slug)
        # ... existing policy check ...

        if redirect_slug:
            # Redirect response — NO _inject_permissions (stays clean)
            return response

        # Set AFTER redirect check
        self._resource = business
        self._inject_permissions = True

        serializer = BusinessAccountOutput(business, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, slug):
        # No self._inject_permissions — PATCH responses don't get _permissions
        ...
```

**Key detail:** `BusinessDetailView` has a redirect path (slug changed). The `_inject_permissions` flag is set AFTER the redirect check so 301 responses don't get `_permissions` injected.

### 5.3 Injection Rules

| HTTP Method | Detail endpoint | List endpoint | Redirect |
|-------------|----------------|---------------|----------|
| **GET** | `_permissions` injected | NOT injected (no opt-in flag) | NOT injected |
| **POST** | N/A | NOT injected (method guard) | N/A |
| **PATCH** | NOT injected (method guard) | N/A | N/A |
| **DELETE** | NOT injected (method guard) | N/A | N/A |

## 6. Backend — Migration

### 0005_update_settings_permission_scopes

Location: `backend/apps/rbac/migrations/0005_update_settings_permission_scopes.py`

**Purpose:** Add `"platform_only"` to `applicable_scopes` for `can_edit_profile` and `can_edit_business` permissions. Without this, Platform Admin role (which only gets `platform_only` scoped permissions) cannot receive these permissions.

| Permission | Before | After |
|------------|--------|-------|
| `can_edit_profile` | `["business", "global_only"]` | `["business", "global_only", "platform_only"]` |
| `can_edit_business` | `["business", "global_only"]` | `["business", "global_only", "platform_only"]` |

Reversible migration (restores original scopes on rollback).

## 7. Frontend — Types

### 7.1 WithPermissions Generic

Location: `frontend/src/types/api.ts`

```typescript
export type WithPermissions<TPerms extends Record<string, boolean>> = {
  _permissions: TPerms;
};
```

### 7.2 Permission Types

Location: `frontend/src/types/organization.ts`

```typescript
export type BusinessPermissions = {
  can_view: boolean;
  can_edit: boolean;
  can_edit_profile: boolean;
  can_delete: boolean;
  can_change_slug: boolean;
  can_archive: boolean;
};

export type PlatformPermissions = {
  can_view: boolean;
  can_edit_profile: boolean;
  can_edit_settings: boolean;
};

// Composed types for detail responses
export type BusinessAccountWithPerms = BusinessAccount &
  WithPermissions<BusinessPermissions>;
export type PlatformAccountWithPerms = PlatformAccount &
  WithPermissions<PlatformPermissions>;
```

**TypeScript gotcha:** Permission types MUST be `type` aliases, NOT `interface`. TypeScript `interface` doesn't satisfy the `Record<string, boolean>` constraint in `WithPermissions<T>`.

### 7.3 API Return Types

| Function | File | Return Type |
|----------|------|-------------|
| `fetchBusinessApi(slug)` | `features/business/api/business-api.ts` | `Promise<BusinessAccountWithPerms>` |
| `fetchPlatformAccountApi()` | `features/platform/api/platform-api.ts` | `Promise<PlatformAccountWithPerms>` |
| `createBusinessApi(data)` | `features/business/api/business-api.ts` | `Promise<BusinessAccount>` (no perms) |
| `updateBusinessApi(slug, data)` | `features/business/api/business-api.ts` | `Promise<BusinessAccount>` (no perms) |
| `updatePlatformProfileApi(data)` | `features/platform/api/platform-api.ts` | `Promise<PlatformProfile>` (no perms) |
| `updatePlatformSettingsApi(data)` | `features/platform/api/platform-api.ts` | `Promise<PlatformAccount>` (no perms) |

**Only GET detail functions return `WithPerms` types.** Mutation responses (POST/PATCH) return base types because the backend doesn't inject `_permissions` into mutation responses.

### 7.4 TanStack Query Integration

The hooks infer return types from `queryFn`, so no changes are needed:

```typescript
// use-business-queries.ts — type flows automatically
export function businessDetailQueryOptions(slug: string) {
  return queryOptions({
    queryKey: queryKeys.business.detail(slug),
    queryFn: () => fetchBusinessApi(slug),  // returns BusinessAccountWithPerms
    staleTime: 5 * 60 * 1000,
    enabled: !!slug,
  });
}

// useBusiness(slug).data is typed as BusinessAccountWithPerms | undefined
```

## 8. Frontend — Can Component

Location: `frontend/src/components/common/Can.tsx`

```tsx
interface CanProps {
  allowed: boolean | undefined;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function Can({ allowed, fallback = null, children }: CanProps) {
  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}
```

**Behavior:**
- `allowed=true` → renders children
- `allowed=false` → renders fallback (default: nothing)
- `allowed=undefined` → renders fallback (safe during loading)

### Usage Patterns

```tsx
// Pattern 1: Simple show/hide
<Can allowed={business._permissions.can_edit}>
  <EditButton />
</Can>

// Pattern 2: View vs Edit with fallback
<Can allowed={business._permissions.can_edit_profile} fallback={<ProfileReadOnly />}>
  <ProfileEditable />
</Can>

// Pattern 3: Danger zone
<Can allowed={business._permissions.can_delete}>
  <DangerZone>
    <DeleteBusinessButton slug={slug} />
  </DangerZone>
</Can>

// Pattern 4: Inline conditional (alternative to <Can>)
{business._permissions.can_change_slug && (
  <ChangeSlugSection business={business} />
)}
```

### Loading State

While data is loading, `_permissions` is `undefined`. Standard query pattern handles this:

```tsx
const { data: business, isLoading } = useBusiness(slug);

if (isLoading) return <Skeleton />;

// Now business._permissions is guaranteed to exist
<Can allowed={business._permissions.can_edit}>
  <EditButton />
</Can>
```

## 9. Key Flows

### Flow 1: GET Business Detail with Permissions

1. Client sends `GET /api/v1/business/acme-corp/`
2. `BusinessDetailView.get()` resolves business by slug
3. Policy check: `BusinessPolicy.can_view(user=user, business=business)`
4. View sets `self._resource = business` and `self._inject_permissions = True`
5. View serializes business → `Response(serializer.data)`
6. `PermissionInjectMixin.finalize_response()` triggers
7. Guards pass: flag is True, method is GET, policy exists, data is dict
8. `BusinessPolicy.get_viewer_permissions(user=user, business=business)` called
9. Policy evaluates 6 permission checks (cached RBAC lookups)
10. `_permissions` dict appended to `response.data`
11. Client receives `{...businessData, _permissions: {can_view: true, ...}}`

### Flow 2: PATCH Business (No Permissions)

1. Client sends `PATCH /api/v1/business/acme-corp/` with `{legal_name: "New Name"}`
2. `BusinessDetailView.patch()` runs — does NOT set `self._inject_permissions`
3. `finalize_response()` triggers but `_inject_permissions` is `False`
4. No `_permissions` injected into response
5. Client receives `{...updatedBusinessData}` (no `_permissions` key)

### Flow 3: GET Business List (No Permissions)

1. Client sends `GET /api/v1/business/`
2. `BusinessListCreateView.get()` runs — does NOT set `self._inject_permissions`
3. Returns paginated response: `{"count": 5, "results": [...]}`
4. `finalize_response()` triggers but flag is `False`
5. Client receives paginated list without `_permissions`

### Flow 4: Frontend Page Renders with Permission Gating

1. User navigates to `/bconsole/acme/settings`
2. `BusinessGuard` validates membership (Tier 1)
3. Page component calls `useBusiness("acme")`
4. TanStack Query fetches `GET /api/v1/business/acme/`
5. Response includes `_permissions: {can_edit: true, can_delete: false, ...}`
6. Component renders:
   - Edit Profile button: visible (`can_edit_profile: true`)
   - Danger Zone / Delete: hidden (`can_delete: false`)
   - Change Slug: hidden (`can_change_slug: false`)
7. User clicks Edit Profile → `PATCH /api/v1/business/acme/profile/`
8. Backend re-validates permission (Tier 3) → success

### Flow 5: Platform Admin RBAC Flow

1. Platform Admin user navigates to `/pconsole/settings`
2. `PlatformGuard` validates platform membership (Tier 1)
3. Page calls `usePlatformAccount()`
4. Backend: `PlatformPolicy.get_viewer_permissions(user=admin_user)`
5. `_has_platform_permission("can_edit_profile")` → checks membership → role → permissions
6. Platform Admin role has `can_edit_profile` with `platform_only` scope → `True`
7. `_has_platform_permission("can_edit_business")` → Platform Admin has it → `True`
8. Response: `_permissions: {can_view: true, can_edit_profile: true, can_edit_settings: true}`
9. Frontend shows full edit UI

## 10. Performance

The RBAC permission lookup per policy method:

1. `MembershipSelector.get_active_membership_for_user_account()` — single indexed query
2. `PermissionSelector.get_permissions_for_membership()` — **cached 5 minutes** (key: `membership_permissions:{id}`)
3. `any(code == permission_code ...)` — O(N) on small set (~10-20 permissions per role)

When `get_viewer_permissions()` calls 3-6 policy methods, they share the same cached permission set from step 2. The membership lookup in step 1 also resolves to the same membership each time.

**Net overhead:** ~2-5ms per GET detail response.

## 11. Gotchas

| Gotcha | Details |
|--------|---------|
| **TypeScript `interface` vs `type`** | `interface` doesn't satisfy `Record<string, boolean>` constraint. Permission types must use `type` alias |
| **Platform has NO Base Member role** | Only 3 roles: Platform Owner (level 0), Platform Admin (level 2), Global Moderator (level 5). No Base Member fallback role |
| **Redirect responses must stay clean** | `BusinessDetailView` has slug redirect logic. Set `_inject_permissions` AFTER redirect check |
| **Permission scopes** | New permissions for Platform must include `platform_only` in `applicable_scopes` or Platform Admin won't receive them |
| **`_safe_check` only for exception-raising policies** | FormTemplatePolicy raises exceptions. BusinessPolicy/PlatformPolicy return booleans. Don't mix patterns |
| **List views must NOT opt in** | Paginated responses are dicts (`{"count": N, "results": [...]}`). Injecting `_permissions` into them would be wrong |
| **`is_staff`/`is_superuser` bypass** | Staff/superuser are Django admin bypass only. The console UI is purely RBAC-driven. Staff bypass in policies is for backend enforcement, not for frontend gating |

## 12. Testing

### Backend Tests

| Module | File | Tests | Status |
|--------|------|-------|--------|
| PermissionInjectMixin | `apps/core/tests/test_views.py` | 6 | Pass |
| PlatformPolicy (all methods) | `apps/organization/tests/platform/test_policies.py` | 20 | Pass |
| BusinessPolicy.get_viewer_permissions | `apps/organization/tests/business/test_policies.py` | 4 | Pass |
| Business view _permissions | `apps/organization/tests/business/test_views.py` | 8 | Pass |
| Platform view _permissions | `apps/organization/tests/platform/test_views.py` | 7 | Pass |
| **Backend Total** | | **45** | **Pass** |

#### Mixin Tests (6)

| Test | Verifies |
|------|----------|
| `test_get_with_flag_injects_permissions` | GET + flag → `_permissions` in response |
| `test_get_without_flag_no_injection` | GET without flag → no `_permissions` |
| `test_post_with_flag_no_injection` | POST + flag → no `_permissions` (GET only) |
| `test_patch_with_flag_no_injection` | PATCH + flag → no `_permissions` (GET only) |
| `test_no_policy_class_no_injection` | GET + flag + no policy → no `_permissions` |
| `test_original_data_preserved` | Original response data preserved alongside `_permissions` |

#### Platform Policy Tests (20)

Tests cover: `can_view`, `can_configure`, `can_update_profile` (staff, superuser, RBAC owner, RBAC admin, non-member), `can_update_settings` (superuser, RBAC owner, RBAC admin, non-member), `get_viewer_permissions` (owner gets all True, admin gets all True, non-member gets view only).

Fixtures: `platform_with_rbac` (ensures roles initialized), `platform_owner_user` (Owner role), `platform_admin_user` (Admin role).

#### Business View Permission Tests (8)

| Test | Verifies |
|------|----------|
| `test_get_response_includes_permissions` | GET detail has `_permissions` dict |
| `test_owner_gets_full_permissions` | Owner: all 6 permissions True |
| `test_non_owner_gets_limited_permissions` | Non-owner: `can_view` True, rest False |
| `test_patch_response_excludes_permissions` | PATCH: no `_permissions` |
| `test_get_by_id_includes_permissions` | GET by UUID: `_permissions` present |
| `test_list_response_excludes_permissions` | GET list: no `_permissions` |
| `test_profile_get_includes_permissions` | GET profile: `_permissions` present |
| `test_profile_patch_excludes_permissions` | PATCH profile: no `_permissions` |

### Frontend Tests

| Module | File | Tests | Status |
|--------|------|-------|--------|
| Can component | `components/common/Can.test.tsx` | 4 | Pass |
| Business API (with perms mock) | `features/business/api/business-api.test.ts` | 6 | Pass |
| Platform API (with perms mock) | `features/platform/api/platform-api.test.ts` | 3 | Pass |
| **Frontend Total** | | **13** | **Pass** |

#### Can Component Tests (4)

| Test | Verifies |
|------|----------|
| `renders children when allowed is true` | `allowed=true` → children visible |
| `renders nothing when allowed is false` | `allowed=false` → empty container |
| `renders fallback when allowed is false and fallback provided` | `allowed=false` + fallback → fallback visible |
| `renders nothing when allowed is undefined` | `allowed=undefined` → safe empty render |

## 13. File Summary

### New Files

| File | Description |
|------|-------------|
| `backend/apps/core/views.py` | `PermissionInjectMixin` — core injection mechanism |
| `backend/apps/core/tests/test_views.py` | 6 mixin isolation tests |
| `backend/apps/rbac/migrations/0005_update_settings_permission_scopes.py` | Adds `platform_only` scope to 2 permissions |
| `backend/apps/organization/tests/platform/test_policies.py` | 20 platform policy RBAC tests |
| `frontend/src/types/api.ts` | `WithPermissions<T>` generic type |
| `frontend/src/components/common/Can.tsx` | Declarative permission gate component |
| `frontend/src/components/common/Can.test.tsx` | 4 Can component tests |

### Modified Files

| File | Change |
|------|--------|
| `backend/apps/organization/platform/policies.py` | Rewritten: added `_has_platform_permission()` RBAC helper, updated `can_update_profile`/`can_update_settings` with RBAC fallback, added `get_viewer_permissions()` |
| `backend/apps/organization/business/policies.py` | Added `get_viewer_permissions()` staticmethod (6 boolean keys) |
| `backend/apps/forms/policies.py` | Added `get_viewer_permissions()` with `_safe_check()` wrapper (4 boolean keys) |
| `backend/apps/organization/business/views.py` | Added `PermissionInjectMixin` to `BusinessByIdView`, `BusinessDetailView`, `BusinessProfileView` |
| `backend/apps/organization/platform/views.py` | Added `PermissionInjectMixin` to `PlatformAccountView`, `PlatformProfileView` |
| `backend/apps/organization/tests/business/test_policies.py` | Added `TestBusinessPolicyGetViewerPermissions` (4 tests) |
| `backend/apps/organization/tests/business/test_views.py` | Added `TestBusinessDetailViewPermissions` (8 tests) |
| `backend/apps/organization/tests/platform/test_views.py` | Added `TestPlatformAccountViewPermissions` (5 tests), `TestPlatformProfileViewPermissions` (2 tests) |
| `frontend/src/types/organization.ts` | Added `BusinessPermissions`, `PlatformPermissions` types + composed `WithPerms` types |
| `frontend/src/features/business/api/business-api.ts` | Updated `fetchBusinessApi` return type to `BusinessAccountWithPerms` |
| `frontend/src/features/platform/api/platform-api.ts` | Updated `fetchPlatformAccountApi` return type to `PlatformAccountWithPerms` |
| `frontend/src/features/business/api/business-api.test.ts` | Updated mock to `BusinessAccountWithPerms` with `_permissions` |
| `frontend/src/features/platform/api/platform-api.test.ts` | Updated mock to `PlatformAccountWithPerms` with `_permissions` |
| `.claude/CLAUDE.md` | Added integration guide for new apps |

## 14. Developer Guide — Adding Permissions to a New App

When building a new app (e.g., CMS Site detail, Notification preferences) that needs `_permissions`:

### Backend Steps

**Step 1 — Policy: Add `get_viewer_permissions()`**

```python
# For bool-returning policies (like BusinessPolicy):
class MyPolicy:
    @staticmethod
    def get_viewer_permissions(*, user, my_resource) -> dict:
        return {
            "can_edit": MyPolicy.can_update(user=user, resource=my_resource),
            "can_delete": MyPolicy.can_delete(user=user, resource=my_resource),
        }

# For exception-raising policies (like FormTemplatePolicy):
class MyPolicy:
    @staticmethod
    def get_viewer_permissions(*, actor_context, my_resource) -> dict:
        def _safe_check(fn, **kwargs) -> bool:
            try:
                fn(**kwargs)
                return True
            except PermissionDenied:
                return False

        return {
            "can_edit": _safe_check(MyPolicy.can_edit, actor_context=actor_context, resource=my_resource),
        }
```

**Step 2 — View: Wire the mixin**

```python
from apps.core.views import PermissionInjectMixin

class MyDetailView(PermissionInjectMixin, APIView):
    policy_class = MyPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "my_resource": self._resource}

    def get(self, request, pk):
        resource = MySelector.get(pk=pk)
        self._resource = resource
        self._inject_permissions = True  # Explicit opt-in
        serializer = MyOutputSerializer(resource)
        return Response(serializer.data)

    def patch(self, request, pk):
        # No _inject_permissions — mutations don't get permissions
        ...
```

**Step 3 — Tests: Verify injection**

```python
class TestMyDetailViewPermissions:
    def test_get_includes_permissions(self, authenticated_client, my_resource):
        response = authenticated_client.get(f"/api/v1/my-resource/{my_resource.id}/")
        assert response.status_code == 200
        assert "_permissions" in response.data
        assert isinstance(response.data["_permissions"], dict)

    def test_patch_excludes_permissions(self, authenticated_client, my_resource):
        response = authenticated_client.patch(
            f"/api/v1/my-resource/{my_resource.id}/",
            {"name": "Updated"}, format="json",
        )
        assert response.status_code == 200
        assert "_permissions" not in response.data

    def test_owner_gets_full_permissions(self, authenticated_client, my_resource):
        response = authenticated_client.get(f"/api/v1/my-resource/{my_resource.id}/")
        perms = response.data["_permissions"]
        assert perms["can_edit"] is True
        assert perms["can_delete"] is True
```

### Frontend Steps

**Step 1 — Types: Add permission type**

```typescript
// types/my-resource.ts
import type { WithPermissions } from "@/types/api";

export type MyResourcePermissions = {
  can_edit: boolean;
  can_delete: boolean;
};

export type MyResourceWithPerms = MyResource & WithPermissions<MyResourcePermissions>;
```

**Step 2 — API: Update return type**

```typescript
export async function fetchMyResourceApi(id: string): Promise<MyResourceWithPerms> {
  const response = await apiClient.get<MyResourceWithPerms>(`/my-resource/${id}/`);
  return response.data;
}
```

**Step 3 — UI: Use `<Can>` component**

```tsx
const { data: resource } = useMyResource(id);

<Can allowed={resource?._permissions.can_edit}>
  <EditButton />
</Can>

<Can allowed={resource?._permissions.can_delete}>
  <DeleteButton />
</Can>
```

**Step 4 — Tests: Update mock data**

```typescript
const mockMyResource: MyResourceWithPerms = {
  ...baseFields,
  _permissions: {
    can_edit: true,
    can_delete: true,
  },
};
```

## 15. Known Limitations

1. **Detail endpoints only** — List endpoints don't include per-item permissions (performance: N items × M policy calls). List pages use Tier 1 (membership store) for page-level action hints.
2. **FormTemplatePolicy not yet wired to views** — `get_viewer_permissions()` exists but the form detail views don't use the mixin yet. Will be wired when the forms frontend is built.
3. **CMS policies not yet implemented** — CMS `get_viewer_permissions()` will be added when the CMS console pages are built.
4. **No cache invalidation on permission change** — If a user's role is changed while they're viewing a detail page, the stale `_permissions` persist until they refresh. TanStack Query's `staleTime: 5min` provides eventual freshness.
5. **Platform membership lookup queries PlatformAccount.objects.first()** — assumes single platform account. Not a problem for current architecture but worth noting.

## 16. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Wire mixin to CMS detail views | `get_viewer_permissions()` ready on FormTemplatePolicy pattern | P1 |
| Wire mixin to FormTemplate detail views | `get_viewer_permissions()` exists, needs view integration | P1 |
| Per-item list permissions | Future: if member list needs "can remove THIS member?" per-row | P2 |
| Permission change real-time update | WebSocket push on role/permission change to invalidate cached data | P3 |

## 17. Related Documents

| Document | Path |
|----------|------|
| System design & concept | `docs/plans/frontend/permission-aware-responses.md` |
| Implementation plan | `C:\Users\AsiaData\.claude\plans\quizzical-tickling-bubble.md` |
| RBAC system reference | `docs/implementations/backend/rbac-system.md` |
| Organization system reference | `docs/implementations/backend/organization-system.md` |
| Frontend foundation reference | `docs/implementations/frontend/frontend-foundation.md` |
| Test standards | `docs/implementations/backend/test-standards.md` |

## 18. Changelog

### v1 (2026-03-02)
- Initial implementation
- Backend: PermissionInjectMixin, 3 policies with get_viewer_permissions(), 5 views wired, migration 0005
- Frontend: WithPermissions<T> generic, BusinessPermissions/PlatformPermissions types, Can component, API type updates
- 45 new backend tests, 4 new frontend tests (+ 9 test mock updates)
- PlatformPolicy refactored from staff-only to RBAC + staff bypass
- Integration guide added to CLAUDE.md
