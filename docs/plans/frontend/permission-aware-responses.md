# Permission-Aware API Responses — System Design

> Centralized, scalable mechanism for embedding RBAC-evaluated permissions
> into backend GET responses, consumed by the frontend for in-page UI gating.

## Clarifications

**`is_staff` / `is_superuser` are NOT part of this system.** Those flags control
Django admin panel access — a completely separate management interface. Staff/superuser
users bypass RBAC automatically at the backend level, but the frontend console UI
(`/bconsole/`, `/pconsole/`) is **purely RBAC-driven**. This document covers only
the RBAC + Organization permission system.

---

## Problem

The frontend has three tiers of authorization:
- **Tier 1**: Membership store (nav hints, route guards) — may be stale
- **Tier 3**: Backend enforcement (always correct, but returns 403 after action)
- **Missing**: In-page UI gating (show/hide edit buttons, panels, actions) with
  **fresh, evaluated** permissions

Currently, in-page gating requires the frontend to manually interpret raw RBAC
permission codes from the membership store. This misses resource-specific conditions
(e.g., `is_system_form`, `is_public`, account status) and can be stale.

## Solution

Add a `_permissions` field to backend GET detail responses. The field contains
**evaluated booleans** — the result of calling Policy methods that check the
requesting user's RBAC membership against the target resource.

```json
GET /api/v1/business/acme-corp/

{
  "id": "uuid",
  "slug": "acme-corp",
  "profile": { "display_name": "Acme Corp", "..." : "..." },
  "_permissions": {
    "can_view": true,
    "can_edit": true,
    "can_edit_profile": true,
    "can_delete": false,
    "can_change_slug": false,
    "can_archive": false
  }
}
```

---

## How It Works

### RBAC Authorization Flow (Recap)

All console authorization follows one path:

```
User → Membership (active, in target account)
  → Role (assigned to membership)
    → RolePermissions (permission codes + scopes)
      → Policy evaluates: has_permission(code)?
        → Also checks: ownership, resource conditions
          → Returns bool
```

The `_permissions` field captures these evaluated booleans at request time.

### Two Policy Signatures in the Codebase

Both are RBAC-based. They differ only in WHERE the membership lookup happens:

| Variant | Used By | Signature | Membership Lookup |
|---------|---------|-----------|-------------------|
| **user + resource** | `BusinessPolicy`, `PlatformPolicy` | `(user, business)` / `(user, platform)` | Inside the policy method |
| **ActorContext + resource** | `FormTemplatePolicy`, CMS policies | `(actor_context, form_template)` | In the view (via AccountContextMixin), before policy call |

Both resolve to the same thing: checking RBAC permission codes from the user's
membership role. The `ActorContext` variant pre-resolves the membership once and
passes the snapshot to multiple policy calls (more efficient for views that check
many permissions).

### BusinessPolicy — get_viewer_permissions()

```python
class BusinessPolicy:
    # ... existing methods unchanged ...

    @staticmethod
    def get_viewer_permissions(*, user, business) -> dict:
        return {
            "can_view": BusinessPolicy.can_view(user=user, business=business),
            "can_edit": BusinessPolicy.can_update(user=user, business=business),
            "can_edit_profile": BusinessPolicy.can_update_profile(user=user, business=business),
            "can_delete": BusinessPolicy.can_delete(user=user, business=business),
            "can_change_slug": BusinessPolicy.can_update_slug(user=user, business=business),
            "can_archive": BusinessPolicy.can_archive(user=user, business=business),
        }
```

Each method internally:
1. Looks up active membership for this user + business
2. Gets cached permissions for that membership (5-min cache)
3. Checks if the required permission code exists
4. Owner-only actions (`can_change_slug`, `can_delete`, `can_archive`) check
   `MembershipSelector.is_user_owner_of_account()` instead of permission codes

### PlatformPolicy — NEEDS UPDATE

**Current state (broken for console use):** PlatformPolicy only checks
`is_staff`/`is_superuser`. This means RBAC Platform Owner/Admin/Moderator roles
have NO effect on platform profile/settings views — they're bypassed entirely.

**Required change:** PlatformPolicy must check RBAC membership, matching the same
pattern as BusinessPolicy. The platform has three RBAC roles with real permissions:

| Role | Level | Permissions |
|------|-------|------------|
| **Platform Owner** | 0 | ALL permissions (all scopes — `platform_and_global` preferred) |
| **Platform Admin** | 2 | `platform_only` scoped permissions |
| **Global Moderator** | 5 | `global_only` scoped permissions |

After update:

```python
class PlatformPolicy:
    @staticmethod
    def _has_platform_permission(*, user, permission_code: str) -> bool:
        """Check if user has a specific permission in their platform membership."""
        platform = PlatformAccount.objects.first()
        if not platform:
            return False
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not membership:
            return False
        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(code == permission_code for code, scope in permissions)

    @staticmethod
    def can_update_profile(*, user) -> bool:
        """Platform Owner or member with can_edit_profile permission."""
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True  # Django admin bypass (separate from RBAC)
        return PlatformPolicy._has_platform_permission(
            user=user, permission_code="can_edit_profile",
        )

    @staticmethod
    def can_update_settings(*, user) -> bool:
        """Platform Owner or member with can_edit_business permission."""
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return PlatformPolicy._has_platform_permission(
            user=user, permission_code="can_edit_business",
        )

    @staticmethod
    def get_viewer_permissions(*, user) -> dict:
        return {
            "can_view": PlatformPolicy.can_view(user=user),
            "can_edit_profile": PlatformPolicy.can_update_profile(user=user),
            "can_edit_settings": PlatformPolicy.can_update_settings(user=user),
        }
```

Now a Platform Owner sees `can_edit_profile: true` via RBAC — no `is_staff` needed.
A Platform Admin sees it too IF their role has `can_edit_profile` with `platform_only` scope.

**Permission seed note:** `can_edit_profile` currently has `applicable_scopes: ["business", "global_only"]`.
For Platform Admin to get it, `"platform_only"` must be added to its applicable scopes.
This requires a data migration update to `0002_seed_permissions.py`.

### FormTemplatePolicy — get_viewer_permissions() (ActorContext variant)

```python
class FormTemplatePolicy:
    # ... existing methods unchanged ...

    @staticmethod
    def get_viewer_permissions(*, actor_context, form_template) -> dict:
        def _safe_check(fn, **kwargs) -> bool:
            try:
                fn(**kwargs)
                return True
            except PermissionDenied:
                return False

        return {
            "can_edit": _safe_check(
                FormTemplatePolicy.can_edit_form,
                actor_context=actor_context, form_template=form_template,
            ),
            "can_delete": _safe_check(
                FormTemplatePolicy.can_delete_form,
                actor_context=actor_context, form_template=form_template,
            ),
            "can_publish": _safe_check(
                FormTemplatePolicy.can_publish_form,
                actor_context=actor_context, form_template=form_template,
            ),
            "can_archive": _safe_check(
                FormTemplatePolicy.can_archive_form,
                actor_context=actor_context, form_template=form_template,
            ),
        }
```

The `_safe_check` helper wraps exception-raising policy methods into booleans.
This handles resource-specific conditions (e.g., `is_system_form` blocks all edits
regardless of permissions).

---

## Backend Implementation

### PermissionInjectMixin

Location: `apps/core/views.py`

**Safety note:** Paginated list responses are also dicts (`{"count": 10, "results": [...]}`).
A naive `isinstance(response.data, dict)` guard would inject `_permissions` into them.
The mixin uses an **explicit opt-in flag** — views must set `self._inject_permissions = True`
in their `get()` method. No flag = no injection. Explicit > implicit.

```python
class PermissionInjectMixin:
    """
    Inject _permissions into GET detail responses.

    Views must:
      1. Set `policy_class = SomePolicy`
      2. Implement `_build_policy_kwargs()` -> dict
      3. Set `self._inject_permissions = True` in get() to opt in

    The opt-in flag prevents accidental injection into paginated list
    responses, error responses, or any other dict-shaped response.
    """
    policy_class = None
    _inject_permissions = False

    def _build_policy_kwargs(self) -> dict:
        """Override to pass correct kwargs to policy.get_viewer_permissions()."""
        raise NotImplementedError

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

### Per-View Wiring

```python
# Business detail view — opt-in to permission injection
class BusinessDetailView(PermissionInjectMixin, APIView):
    policy_class = BusinessPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "business": self._resource}

    def get(self, request, slug):
        business = BusinessAccountSelector.get_by_slug(slug=slug)
        self._resource = business
        self._inject_permissions = True     # opt-in
        # ... rest of existing code unchanged ...

    def patch(self, request, slug):
        # No self._inject_permissions — PATCH responses don't get _permissions
        # ... existing code unchanged ...

# Business LIST view — mixin inherited but NOT opted in
class BusinessListCreateView(PermissionInjectMixin, APIView):
    policy_class = BusinessPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "business": self._resource}

    def get(self, request):
        # No self._inject_permissions = True → paginated response stays clean
        businesses = BusinessAccountSelector.list_active()
        # ... returns {"count": N, "results": [...]} — no _permissions injected

# Platform views
class PlatformAccountView(PermissionInjectMixin, APIView):
    policy_class = PlatformPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user}

    def get(self, request):
        platform = PlatformAccountSelector.get()
        self._resource = platform
        self._inject_permissions = True
        # ... rest unchanged ...

# Form views (ActorContext variant)
class FormTemplateDetailView(PermissionInjectMixin, FormViewMixin, APIView):
    policy_class = FormTemplatePolicy

    def _build_policy_kwargs(self):
        return {"actor_context": self._actor_context, "form_template": self._resource}

    def get(self, request, ...):
        actor_context = self.get_actor_context()
        self._actor_context = actor_context
        template = FormTemplateSelector.get(...)
        self._resource = template
        self._inject_permissions = True
        # ... rest unchanged ...
```

### Detail vs List Endpoints

- **Detail endpoints**: Include `_permissions` (evaluated per-resource)
- **List endpoints**: Do NOT include `_permissions` (performance: N items x M policy calls)

For lists, the frontend uses Tier 1 (membership store) for page-level action hints.
Example: "show Invite button" on member list → check membership store for
`can_invite_member`. This is page-level (same for all items), not per-item.

If future features need per-item permissions (e.g., "can remove THIS member but
not THAT one" based on role levels), that will be handled by a separate mechanism
on specific list endpoints — not by this mixin.

### Performance

The RBAC permission lookup:
1. `MembershipSelector.get_active_membership_for_user_account()` — single indexed query
2. `PermissionSelector.get_permissions_for_membership()` — **cached 5 minutes**
   (key: `membership_permissions:{id}`)
3. `any(code == permission_code ...)` — O(N) on small set (~10-20 permissions per role)

When `get_viewer_permissions()` calls 6-7 policy methods, all share the same cached
permission set from step 2. The membership lookup in step 1 also resolves to the
same membership each time. Net overhead: **~2-5ms** per GET response.

---

## Frontend Consumption

### TypeScript Types

```typescript
// types/api.ts (NEW)

/** Generic wrapper: resource data + evaluated permissions */
export type WithPermissions<TPerms extends Record<string, boolean>> = {
  _permissions: TPerms;
};

// types/organization.ts (UPDATED)

export interface BusinessPermissions {
  can_view: boolean;
  can_edit: boolean;
  can_edit_profile: boolean;
  can_delete: boolean;
  can_change_slug: boolean;
  can_archive: boolean;
}

export interface PlatformPermissions {
  can_view: boolean;
  can_edit_profile: boolean;
  can_edit_settings: boolean;
}

// Extend existing types
export type BusinessAccountWithPerms = BusinessAccount & WithPermissions<BusinessPermissions>;
export type PlatformAccountWithPerms = PlatformAccount & WithPermissions<PlatformPermissions>;
```

### API Functions

```typescript
// features/business/api/business-api.ts — update return type
export async function fetchBusinessApi(slug: string): Promise<BusinessAccountWithPerms> {
  const response = await apiClient.get<BusinessAccountWithPerms>(`/business/${slug}/`);
  return response.data;
}

// features/platform/api/platform-api.ts — update return type
export async function fetchPlatformAccountApi(): Promise<PlatformAccountWithPerms> {
  const response = await apiClient.get<PlatformAccountWithPerms>("/platform/account/");
  return response.data;
}
```

### In-Page Usage (Inline Conditionals)

```tsx
// Business settings page
const { data: business } = useBusinessDetail(slug);

{business._permissions.can_edit_profile && (
  <Button onClick={() => setEditing(true)}>Edit Profile</Button>
)}

{business._permissions.can_change_slug && (
  <ChangeSlugSection business={business} />
)}

{business._permissions.can_delete && (
  <DangerZone>
    <DeleteBusinessButton slug={slug} />
  </DangerZone>
)}
```

### Optional: `<Can>` Convenience Component

```tsx
// components/common/Can.tsx
interface CanProps {
  allowed: boolean | undefined;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

function Can({ allowed, fallback = null, children }: CanProps) {
  if (!allowed) return <>{fallback}</>;
  return <>{children}</>;
}

// Usage — especially useful for view-vs-edit patterns:
<Can allowed={business._permissions.can_edit_profile} fallback={<ProfileReadOnly />}>
  <ProfileEditable />
</Can>
```

Simple wrapper. No magic. Works with any boolean. The `fallback` prop avoids
ternary clutter when showing alternative content for denied users.

### Loading State

While data is loading, `_permissions` is `undefined`. Components should handle this:

```tsx
const { data: business, isLoading } = useBusinessDetail(slug);

if (isLoading) return <Skeleton />;

// Now business._permissions is guaranteed to exist
```

This is already the standard pattern — query data is `undefined` during loading.
No special permission handling needed.

---

## Three-Tier Authorization Model (Final)

```
Tier 1: Membership Store (EXISTING — unchanged)
├── Source: fetchMyMembershipsApi() on login + window refocus
├── Data: Raw RBAC permission codes per membership
├── Used for:
│   ├── Nav sidebar filtering (useFilteredNav)
│   ├── Route guards (BusinessGuard, PlatformGuard)
│   └── Page-level action hints on list pages (can_invite_member, etc.)
├── Speed: Instant (Zustand), may be stale
└── Limitation: No resource-specific logic (is_system_form, account status, etc.)

Tier 1.5: Response Permissions (NEW)
├── Source: _permissions field in GET detail responses
├── Data: Evaluated booleans from Policy.get_viewer_permissions()
├── Used for:
│   ├── In-page UI gating (edit buttons, panels, danger zones)
│   ├── View-vs-edit rendering (fallback pattern)
│   └── Resource-specific permission display
├── Speed: Always fresh (evaluated at request time via RBAC)
├── Handles: Owner-only actions, resource conditions
│           (is_public, is_system_form, account status, etc.)
└── Scope: Detail endpoints only (not lists)

Tier 3: Backend Enforcement (EXISTING — unchanged)
├── Source: Policy checks on every POST/PATCH/DELETE
├── Returns: 403 PermissionDenied if unauthorized
└── Authority: Final — always enforced regardless of frontend
```

### How They Work Together

| Scenario | Tier Used | Why |
|----------|-----------|-----|
| Show/hide "Members" in sidebar | Tier 1 (membership store) | Nav renders before any data fetch |
| Block `/bconsole/acme/` route for non-member | Tier 1 (route guard) | Guard runs before page renders |
| Show "Invite Member" button on members page | Tier 1 (membership store) | Page-level action, uniform for all items |
| Show "Edit Profile" button on business detail | **Tier 1.5** (`_permissions`) | Resource-specific, RBAC-evaluated |
| Show "Delete Business" in danger zone | **Tier 1.5** (`_permissions`) | Owner-only, policy-evaluated |
| Show "Edit" vs "View Only" on settings page | **Tier 1.5** (`_permissions`) | View-vs-edit pattern |
| Reject unauthorized PATCH request | Tier 3 (backend) | Always checked, returns 403 |

### RBAC Role Hierarchy

**Business Account** (created by `initialize_business_account`):

| Role | Level | Permissions | System Role |
|------|-------|------------|-------------|
| **Owner** | 0 | All `business`-scoped permissions | Yes (immutable) |
| *(Custom roles)* | 1-9 | Configurable per business | No |
| **Base Member** | 10 | **Zero permissions** (fallback) | Yes (immutable) |

**Platform Account** (created by `initialize_platform_account`):

| Role | Level | Scopes | System Role |
|------|-------|--------|-------------|
| **Platform Owner** | 0 | All permissions, broadest scope (`platform_and_global` preferred) | Yes |
| **Platform Admin** | 2 | `platform_only` scoped permissions | No (configurable) |
| **Global Moderator** | 5 | `global_only` scoped permissions (cross-account actions) | No (configurable) |

### Fallback Role Behavior

When a membership is created without a valid role, it falls back to **Base Member**:
- Level 10 (lowest authority)
- **Zero permissions** (empty permission set)
- CAN access the console (has active membership → guard passes)
- CAN see ungated nav items (Dashboard)
- CANNOT see any gated nav items (no permission codes)
- Gets `_permissions: { can_edit: false, can_edit_profile: false, ... }` on every detail endpoint

This is the intended "read-only member" experience — they can view but not modify.

---

## Scope of Changes

### Backend Changes

| File | Change |
|------|--------|
| `apps/core/views.py` | Add `PermissionInjectMixin` class |
| `apps/organization/business/policies.py` | Add `get_viewer_permissions()` staticmethod |
| `apps/organization/platform/policies.py` | **Refactor:** add `_has_platform_permission()` helper + RBAC-based checks for `can_update_profile`, `can_update_settings`. Add `get_viewer_permissions()` |
| `apps/rbac/migrations/` | **New migration:** add `"platform_only"` to `can_edit_profile` and `can_edit_business` applicable_scopes (so Platform Admin can receive these permissions) |
| `apps/forms/policies.py` | Add `get_viewer_permissions()` staticmethod (+ `_safe_check` helper) |
| `apps/cms/policies.py` | Add `get_viewer_permissions()` staticmethod (when needed) |
| `apps/organization/business/views.py` | Add mixin to `BusinessDetailView`, `BusinessByIdView`, `BusinessProfileView` |
| `apps/organization/platform/views.py` | Add mixin to `PlatformAccountView`, `PlatformProfileView` |

### Frontend Changes

| File | Change |
|------|--------|
| `types/api.ts` | New: `WithPermissions<T>` generic type |
| `types/organization.ts` | Add `BusinessPermissions`, `PlatformPermissions` interfaces + composed types |
| `features/business/api/business-api.ts` | Update `fetchBusinessApi` return type |
| `features/platform/api/platform-api.ts` | Update `fetchPlatformAccountApi` return type |
| `components/common/Can.tsx` | New: optional convenience component |

### Files NOT Changed

| File | Why |
|------|-----|
| `stores/membership-store.ts` | Tier 1 stays unchanged |
| `hooks/use-has-permission.ts` | Kept as low-level primitive for edge cases |
| `hooks/use-filtered-nav.ts` | Still reads membership store for nav filtering |
| `hooks/use-nav-context.ts` | Unchanged |
| `lib/navigation-config.ts` | Unchanged |
| Guards (`AuthGuard`, `BusinessGuard`, etc.) | Unchanged |

---

## Future Extensibility

### Adding a New Resource

When a new resource type (e.g., CMS Site) needs `_permissions`:

1. Add `get_viewer_permissions()` to its policy class
2. Add `PermissionInjectMixin` to its detail view
3. Add TypeScript permission interface on frontend
4. Consume `_permissions` in the page component

No changes to shared infrastructure.

### Per-Item List Permissions (Future)

If member list needs "can remove THIS member?" per-row:

Option A: Add `_permissions` per-item on that specific list endpoint (not global).
The mixin skips lists by default; the view manually injects per-item.

Option B: Keep page-level Tier 1 check for button visibility, handle
role-level rejection via backend 403 + error toast.

### AccountContext (Future, Optional)

If multiple sibling components on the same page need the same accountId/slug
without prop drilling, add a lightweight `AccountContext` that wraps console
layouts inside the guard. This is orthogonal to `_permissions` — it provides
convenience for mutation calls and non-data-fetch scenarios.

Not needed for the initial business/platform profile pages.
