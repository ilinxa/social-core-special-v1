---
name: rbac-integration
description: Use when adding authorization, permissions, or access control to ANY Django app or feature in this project. Triggers on: creating views/services that need permission checks, adding new permissions to the registry, creating data migrations for permissions, wiring MembershipPolicy into service methods, building ActorContext in views, creating roles, checking ownership, moderating content cross-account, or any mention of RBAC, permissions, roles, memberships, authorization, access control, can_*, or policy checks. Also use when creating a new Django app that needs to integrate with the existing RBAC system. MUST be used before writing any authorization logic — never hand-roll permission checks.
---

# RBAC Integration Skill

All RBAC code is in `backend/apps/rbac/`. Core types in `backend/apps/core/types.py` and `backend/apps/core/constants.py`.

## Quick Start — Adding Authorization to Any Service

```python
from apps.core.types import ActorContext
from apps.core.constants import AccountType
from apps.rbac.policies import MembershipPolicy
from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService

# In your service method:
def your_action(*, actor_context: ActorContext, **kwargs):
    MembershipPolicy.authorize_action(
        actor_context=actor_context,
        target_membership=None,  # None = checking actor's own permission
        required_permission="can_your_action",
    )
    # ... do work, then audit ...
```

```python
# In your view:
from apps.rbac.views import BusinessContextMixin  # or PlatformContextMixin

class YourView(BusinessContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, business_slug):
        actor_context = self.get_actor_context()
        YourService.your_action(actor_context=actor_context, ...)
```

---

## The Authorization Algorithm (4 steps)

`MembershipPolicy.authorize_action()` does this:

1. **Actor must have active membership** (enforced by `build_actor_context`)
2. **Same-account vs cross-account?** Compare actor's `(account_type, account_id)` vs target's
3. **Permission check:**
   - Same-account → `actor_context.has_permission(code)` (any scope)
   - Cross-account → `actor_context.has_global_permission(code)` (only `global_only` or `platform_and_global`)
4. **Target checks** (if target_membership provided):
   - Owner invincibility: same-account owner = DENIED; platform owner = ALWAYS DENIED; business owner + cross-account = ALLOWED
   - Dominance: same-account `actor.role_level >= target.role.level` = DENIED; cross-account = SKIPPED

---

## Permission Scopes

| Scope | Meaning | When to use |
|-------|---------|-------------|
| `business` | Within the business where role is assigned | Most business actions (CRUD, view) |
| `platform_only` | Within the platform account only | Platform internal management |
| `global_only` | Cross-account (platform → business) | Platform moderating business content |
| `platform_and_global` | Both platform internal + cross-account | Rare — only `can_view_audit_logs` uses this |

**Decision rule:** If platform staff should be able to do this action on a business remotely, include `global_only`. If not, don't.

---

## Adding New Permissions (3-step process)

### Step 1: Add to registry

```python
# backend/apps/rbac/permissions/registry.py — add to PERMISSIONS list:
(
    "can_create_post",
    "Create Post",
    "Create new posts in the account",
    "content",                          # new category
    ["business"],                       # applicable_scopes
),
(
    "can_delete_post",
    "Delete Post",
    "Delete posts",
    "content",
    ["business", "global_only"],        # business + platform moderation
),
```

### Step 2: Create data migration

```python
# backend/apps/rbac/migrations/000X_seed_content_permissions.py
from django.db import migrations

CONTENT_PERMISSIONS = [
    ("can_create_post", "Create Post", "Create new posts", "content", ["business"]),
    ("can_delete_post", "Delete Post", "Delete posts", "content", ["business", "global_only"]),
]

def seed(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    for code, name, desc, cat, scopes in CONTENT_PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={'name': name, 'description': desc, 'category': cat, 'applicable_scopes': scopes}
        )

def reverse(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Permission.objects.filter(code__in=[p[0] for p in CONTENT_PERMISSIONS]).delete()

class Migration(migrations.Migration):
    dependencies = [('rbac', 'XXXX_previous')]
    operations = [migrations.RunPython(seed, reverse)]
```

### Step 3: Backfill existing accounts

New businesses auto-get permissions (via `initialize_business_account`). Existing businesses do NOT. Create a backfill migration:

```python
def backfill(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Role = apps.get_model('rbac', 'Role')
    RolePermission = apps.get_model('rbac', 'RolePermission')

    new_perms = Permission.objects.filter(category='content')
    owner_roles = Role.objects.filter(account_type='business', level=0, is_system_role=True)

    for role in owner_roles:
        for perm in new_perms:
            if 'business' in (perm.applicable_scopes or []):
                RolePermission.objects.get_or_create(
                    role=role, permission=perm,
                    defaults={'scope': 'business'}
                )

    # Also backfill platform roles if permissions have global_only scope
    platform_owner = Role.objects.filter(account_type='platform', level=0, is_system_role=True)
    global_mod = Role.objects.filter(account_type='platform', level=5)

    for role in platform_owner:
        for perm in new_perms:
            scope = 'global_only' if 'global_only' in (perm.applicable_scopes or []) else 'business'
            RolePermission.objects.get_or_create(
                role=role, permission=perm, defaults={'scope': scope}
            )
    for role in global_mod:
        for perm in new_perms:
            if 'global_only' in (perm.applicable_scopes or []):
                RolePermission.objects.get_or_create(
                    role=role, permission=perm, defaults={'scope': 'global_only'}
                )
```

---

## Current Permission Registry (26 permissions)

| Category | Permissions | Scopes |
|----------|------------|--------|
| membership (7) | `can_invite_member`, `can_remove_member`, `can_change_member_role`, `can_suspend_member`, `can_ban_member`, `can_approve_membership_request`, `can_view_members` | business + global/platform variants |
| roles (3) | `can_create_role`, `can_edit_role`, `can_delete_role` | business, platform_only (NO global) |
| settings (3) | `can_edit_business`, `can_edit_profile`, `can_view_settings` | business + global/platform variants |
| platform (6) | `can_suspend_business`, `can_remove_business_owner`, `can_transfer_business_ownership`, `can_view_businesses`, `can_approve_verification_request`, `can_approve_business_creation` | global_only and/or platform_only |
| audit (1) | `can_view_audit_logs` | all four scopes |
| forms (6) | `can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`, `can_export_responses`, `can_process_response` | business + platform/global variants |

---

## Authorization Patterns

### Pattern 1: Service-level auth (STANDARD — use this)

```python
class PostService:
    @staticmethod
    @transaction.atomic
    def create_post(*, actor_context: ActorContext, business_id, content, request=None):
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,
            required_permission="can_create_post",
        )
        post = Post.objects.create(author_id=actor_context.user_id, business_id=business_id, content=content)
        AuditService.log(action=AuditLog.Action.POST_CREATED, actor=_resolve_actor(actor_context), resource=post, request=request)
        return post
```

### Pattern 2: Author + permission dual check

Author always edits own content; others need moderation permission.

```python
def edit_post(*, actor_context: ActorContext, post, changes, request=None):
    if post.author_id != actor_context.user_id:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,
            required_permission="can_edit_post",
        )
    # ... apply changes ...
```

### Pattern 3: Membership-only check (no permission needed)

For low-barrier actions (view feed, react, comment):

```python
# In view — just verify membership exists
membership = MembershipSelector.get_active_membership_for_user_account(
    user=request.user, account_type=AccountType.BUSINESS, account_id=business.id,
)
if not membership:
    raise PermissionDenied(message="You are not a member of this business")
```

### Pattern 4: Owner-only (non-delegatable)

For critical actions (delete business, change plan). Use `is_owner`, NOT a permission.

```python
if not actor_context.is_owner:
    raise PermissionDenied(message="Only the account owner can perform this action")
```

### Pattern 5: Cross-account moderation

Platform staff moderating business content:

```python
def platform_delete_post(*, actor_context: ActorContext, post, request=None):
    # actor_context is platform membership. target=None means just check permission.
    # has_global_permission is checked automatically because actor is platform, post is business.
    # For simple cases, you can also check directly:
    if not actor_context.has_global_permission("can_delete_post"):
        raise PermissionDenied(message="Missing global permission")
    # ... delete ...
```

---

## View Layer Wiring

### Business context (most common)

```python
class YourView(BusinessContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, business_slug):
        actor_context = self.get_actor_context()  # builds ActorContext from membership
        result = YourService.your_action(actor_context=actor_context, business_id=self.get_account_id(), ...)
        return Response(YourSerializer(result).data, status=status.HTTP_201_CREATED)
```

### Platform context

```python
class YourPlatformView(PlatformContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        actor_context = self.get_actor_context()
        # ...
```

### No RBAC context (user-level)

```python
# For actions tied to the user, not an account:
actor_context = ActorContext.for_user_context(user=request.user, request=request)
```

---

## Role Hierarchy Reference

### Business plane

```
Owner (L0, is_owner=True)  ← invincible within business, gets ALL business-scope perms
  Custom Admin (L1-2)      ← manually assigned permissions
  Custom Editor (L3-5)     ← manually assigned permissions
  Custom Viewer (L6-9)     ← manually assigned permissions
Base Member (L10)          ← zero permissions
```

### Platform plane

```
Platform Owner (L0)      ← truly invincible, ALL permissions (broadest scope each)
Platform Admin (L2)      ← platform_only scope perms (no cross-account)
Global Moderator (L5)    ← global_only scope perms (cross-account moderation)
```

**Dominance rule:** `actor.role_level < target.role.level` required (lower number = higher authority). Equal levels cannot act on each other. Skipped for cross-account actions.

---

## Anti-Patterns — NEVER Do These

### ❌ Never check permissions in views

```python
# WRONG — authorization in view bypasses service callers
def post(self, request, business_slug):
    actor = self.get_actor_context()
    if not actor.has_permission("can_create_post"):  # BAD
        raise PermissionDenied(...)
    PostService.create_post(content=request.data)  # service has no auth
```

Always put `MembershipPolicy.authorize_action()` inside the service method.

### ❌ Never check role name

```python
# WRONG — role names are display strings, custom roles can have any name
if actor_context.role_name == "Admin":  # BAD
```

Check permissions or `role_level`, never `role_name`.

### ❌ Never query RolePermission directly

```python
# WRONG — bypasses caching, scope resolution, and ActorContext snapshot
perms = RolePermission.objects.filter(role__memberships__user=user)  # BAD
```

Always go through `RBACService.build_actor_context()` → `MembershipPolicy.authorize_action()`.

### ❌ Never create permissions via admin/API

Permissions are immutable after migration. Add to `registry.py` → create data migration. Never `Permission.objects.create()` in service code.

### ❌ Never make owner-only actions permission-based

```python
# WRONG — owner-only actions should not be delegatable
("can_delete_business", "Delete Business", ..., "settings", ["business"]),  # BAD
```

If only the owner should do it, check `actor_context.is_owner` directly.

### ❌ Never forget the backfill migration

Adding a new permission to registry + seed migration only affects NEW accounts. Existing business Owner roles won't get it. Always create a backfill migration (see Step 3 above).

### ❌ Never add `global_only` scope to role management permissions

```python
# WRONG — platform staff should NOT remotely create/edit/delete roles inside businesses
("can_create_role", ..., ["business", "platform_only", "global_only"]),  # BAD
```

Role management is business-internal. Platform staff moderate members, not role structures.

---

## Existing Permissions Not Yet Wired

These permissions exist in the registry but their consuming apps haven't integrated them yet:

| Permission | Waiting for |
|-----------|-------------|
| `can_edit_business`, `can_edit_profile`, `can_view_settings` | Organization app service/views |
| `can_suspend_business`, `can_remove_business_owner`, `can_transfer_business_ownership` | Organization app platform actions |
| `can_view_businesses`, `can_approve_verification_request`, `can_approve_business_creation` | Organization app platform views |
| `can_view_audit_logs` | Audit log view endpoints |
| `can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`, `can_export_responses`, `can_process_response` | Form Builder service layer |

When building these apps, use the existing permissions — do NOT create duplicates.

---

## Testing New Integrations

For every service method that calls `MembershipPolicy.authorize_action()`, write:

```python
# 1. Permission denied
def test_create_post_requires_permission(self):
    actor = build_actor_context(permissions=[])
    with pytest.raises(PermissionDenied):
        PostService.create_post(actor_context=actor, ...)

# 2. Permission granted
def test_create_post_with_permission(self):
    actor = build_actor_context(permissions=[("can_create_post", "business")])
    post = PostService.create_post(actor_context=actor, ...)
    assert post is not None

# 3. Cross-account scope boundary
def test_business_scope_cannot_cross_accounts(self):
    admin_a = build_actor_context(account_id=biz_a.id, permissions=[("can_delete_post", "business")])
    with pytest.raises(PermissionDenied):
        PostService.delete_post(actor_context=admin_a, post=post_in_biz_b)

# 4. Audit trail
@mock.patch('apps.content.services.AuditService.log')
def test_create_post_audited(self, mock_log):
    PostService.create_post(actor_context=admin_actor, ...)
    mock_log.assert_called_once()
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `apps/rbac/permissions/registry.py` | Permission definitions (source of truth) |
| `apps/rbac/policies.py` | `MembershipPolicy.authorize_action()`, `RolePolicy` |
| `apps/rbac/services.py` | `RBACService` — all write operations |
| `apps/rbac/selectors.py` | `MembershipSelector`, `PermissionSelector`, `RoleSelector` |
| `apps/rbac/views.py` | `BusinessContextMixin`, `PlatformContextMixin`, `AccountContextMixin` |
| `apps/rbac/models.py` | `Permission`, `Role`, `RolePermission`, `Membership` |
| `apps/core/types.py` | `ActorContext` dataclass |
| `apps/core/constants.py` | `AccountType`, `PermissionScope`, `MembershipStatus` |