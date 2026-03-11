# RBAC Integration Playbook

**Purpose:** Step-by-step reference for integrating the RBAC system with every app in the platform — current and future.
**Use this document:** Every time you build a new app, add a feature that needs authorization, or extend an existing app with new capabilities.

---

## Table of Contents

1. [How To Use This Document](#1-how-to-use-this-document)
2. [Integration Checklist (Universal)](#2-integration-checklist-universal)
3. [Current System Map](#3-current-system-map)
4. [Organization System Integration](#4-organization-system-integration)
5. [Request / Invitation / Confirmation System Integration](#5-request--invitation--confirmation-system-integration)
6. [Form Builder System Integration](#6-form-builder-system-integration)
7. [Content System Integration (Future)](#7-content-system-integration-future)
8. [Notification System Integration (Future)](#8-notification-system-integration-future)
9. [Messaging / Chat System Integration (Future)](#9-messaging--chat-system-integration-future)
10. [Analytics / Reporting System Integration (Future)](#10-analytics--reporting-system-integration-future)
11. [Billing / Subscription System Integration (Future)](#11-billing--subscription-system-integration-future)
12. [File / Media Management Integration (Future)](#12-file--media-management-integration-future)
13. [Permission Registry Evolution Plan](#13-permission-registry-evolution-plan)
14. [Migration Strategy](#14-migration-strategy)
15. [Patterns & Anti-Patterns](#15-patterns--anti-patterns)
16. [Role Seeding Updates](#16-role-seeding-updates)
17. [Testing Strategy for New Integrations](#17-testing-strategy-for-new-integrations)

---

## 1. How To Use This Document

When you start working on any app:

**Step 1 — Find your app's section** (§4–§12). Read the predicted permissions, scope decisions, and authorization points.

**Step 2 — Update the Permission Registry** (§13–§14). Add new permissions to `registry.py`, create a data migration, and update initialization logic.

**Step 3 — Wire authorization into your service layer** using the patterns in §15.

**Step 4 — Write tests** following §17.

Every section follows the same structure: what the app does, what actions need authorization, what permissions are needed, what scopes they use, which roles get them by default, and exactly where in the code to call `MembershipPolicy.authorize_action()`.

---

## 2. Integration Checklist (Universal)

Use this checklist every time you add RBAC to a new app or feature:

```
□ 1. DEFINE PERMISSIONS
    □ List every action that requires authorization
    □ Determine applicable_scopes for each (business? platform_only? global_only?)
    □ Choose a category name for the registry
    □ Add to PERMISSIONS list in permissions/registry.py

□ 2. CREATE DATA MIGRATION
    □ New migration file: 000X_seed_{app}_permissions.py
    □ Use get_or_create pattern (idempotent)
    □ Add reverse migration (delete by codes)

□ 3. UPDATE ROLE INITIALIZATION
    □ Business Owner gets business-scoped permissions automatically
    □ Platform Owner gets broadest scope automatically
    □ Decide: Does Platform Admin get platform_only for these?
    □ Decide: Does Global Moderator get global_only for these?
    □ NO code changes needed if you follow the existing pattern
      (initialize_business_account seeds ALL business-scope perms to Owner)

□ 4. WIRE INTO SERVICE LAYER
    □ Import MembershipPolicy, ActorContext
    □ Add actor_context parameter to service methods
    □ Call MembershipPolicy.authorize_action() before mutations
    □ Call AuditService.log() after mutations

□ 5. WIRE INTO VIEW LAYER
    □ Use BusinessContextMixin or PlatformContextMixin
    □ Call self.get_actor_context() in view methods
    □ Pass actor_context to service methods

□ 6. WRITE TESTS
    □ Service tests: permission required, permission denied
    □ Actor scenario tests: each role type for each action
    □ Scope boundary tests: business scope can't cross accounts
    □ Audit trail tests: mock AuditService.log

□ 7. UPDATE DOCUMENTATION
    □ Update this playbook's section for the app
    □ Mark predictions as "IMPLEMENTED" with actual permission codes
```

---

## 3. Current System Map

### What Exists Today

```
┌─────────────────────────────────────────────────────────────┐
│                         Platform                            │
│                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│   │  Organization │  │     RBAC     │  │  Form Builder    │ │
│   │  System       │  │   System     │  │  System          │ │
│   │              │  │  (25 perms)  │  │  (6 perms exist) │ │
│   │  • Platform  │  │              │  │  • Form CRUD     │ │
│   │  • Business  │  │  • Membership│  │  • Responses     │ │
│   │  • Verif.    │  │  • Roles     │  │                  │ │
│   └──────┬───────┘  │  • Policies  │  └──────────────────┘ │
│          │          └──────┬───────┘                        │
│          │                 │                                │
│   ┌──────▼─────────────────▼────────────────────────────┐  │
│   │           Request / Invitation / Confirmation        │  │
│   │           (Transaction System)                       │  │
│   │           • Invitation → create_membership()         │  │
│   │           • Ownership Transfer (STUB)                │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌──────────────────────────────────────────────────────┐  │
│   │              FUTURE APPS                              │  │
│   │  Content · Notifications · Chat · Analytics · Billing │  │
│   │  Media · Marketplace · API Keys · Webhooks            │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Current Permission Count: 25

| Category | Count | Status |
|----------|-------|--------|
| membership | 7 | ✅ Fully integrated with RBAC views |
| roles | 3 | ✅ Fully integrated with RBAC views |
| settings | 3 | ⚠️ Permissions exist, Organization app needs to consume them |
| platform | 6 | ⚠️ Permissions exist, Organization app needs to consume them |
| audit | 1 | ⚠️ Permission exists, Audit views need to consume it |
| forms | 6 | ⚠️ Permissions exist, Form Builder needs to consume them |

The key insight: **21 of 25 permissions are already used by RBAC's own views for membership/role management. The other 15 permissions (settings, platform, audit, forms) exist in the registry but are waiting for their respective apps to consume them.**

---

## 4. Organization System Integration

The Organization system manages `BusinessAccount` and `PlatformAccount` lifecycle. It's the first consumer of RBAC outside of RBAC itself.

### 4.1 Business Account CRUD

| Action | Who Can Do It | Permission Needed | Scope | Status |
|--------|---------------|-------------------|-------|--------|
| Create business | Any authenticated user | None (user-level action) | N/A | ⚠️ Needs `can_approve_business_creation` if approval flow exists |
| View own business | Any member of business | Membership check only | N/A | 🔲 NOT WIRED |
| Edit business settings | Business Owner, Admin | `can_edit_business` | business | 🔲 NOT WIRED |
| Edit business profile | Business Owner, Admin | `can_edit_profile` | business | 🔲 NOT WIRED |
| View business settings | Members with perm | `can_view_settings` | business | 🔲 NOT WIRED |
| Delete / archive business | Business Owner only | `is_owner` check | N/A | 🔲 NOT WIRED |
| Suspend business (platform) | Platform Admin/Owner | `can_suspend_business` | global_only | 🔲 NOT WIRED |
| View all businesses (platform) | Platform staff | `can_view_businesses` | global_only, platform_only | 🔲 NOT WIRED |

**Implementation pattern for Business edit:**

```python
# In apps/organization/business/services.py

class BusinessService:
    @staticmethod
    @transaction.atomic
    def update_business(
        *,
        business_id: UUID,
        actor_context: ActorContext,
        changes: dict,
        request=None
    ) -> BusinessAccount:
        business = BusinessAccount.objects.get(id=business_id)

        # RBAC check
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,  # No target member, checking actor's permission
            required_permission="can_edit_business",
        )

        # ... apply changes, audit log ...
```

### 4.2 Business Verification

| Action | Permission Needed | Scope |
|--------|-------------------|-------|
| Submit verification request | `is_owner` or `can_edit_business` | business |
| Approve verification | `can_approve_verification_request` | platform_only, global_only |
| Reject verification | `can_approve_verification_request` | platform_only, global_only |
| View verification status (own) | Any business member | membership check |
| View all verification requests | `can_approve_verification_request` | platform_only |

### 4.3 Business Creation Approval Flow

If the platform requires approval for new businesses:

| Action | Permission Needed | Scope |
|--------|-------------------|-------|
| Submit business creation request | Any authenticated user | N/A |
| Approve creation request | `can_approve_business_creation` | platform_only |
| Reject creation request | `can_approve_business_creation` | platform_only |

**Note:** After approval, `RBACService.initialize_business_account()` is called automatically. The approver doesn't need RBAC membership permissions — they need the platform permission to approve the request.

### 4.4 Platform Account Management

| Action | Permission Needed | Scope |
|--------|-------------------|-------|
| View platform dashboard | Platform membership check | N/A |
| Edit platform settings | Platform Owner only | `is_owner` check |
| Suspend a business | `can_suspend_business` | global_only |
| Remove business owner | `can_remove_business_owner` | global_only |
| Force ownership transfer | `can_transfer_business_ownership` | global_only |

### 4.5 New Permissions Needed: NONE

All Organization permissions already exist in the registry. The work is purely wiring them into the Organization service/view layer.

---

## 5. Request / Invitation / Confirmation System Integration

This system (Transaction System) handles workflow requests: invitations, membership requests, ownership transfer, verification requests.

### 5.1 Invitation Flow

| Action | Permission Needed | Scope | Notes |
|--------|-------------------|-------|-------|
| Send invitation to join business | `can_invite_member` | business | Business-internal invitation |
| Send invitation to join platform | `can_invite_member` | platform_only | Platform staff inviting new staff |
| Cancel own sent invitation | Invitation creator check | N/A | Not RBAC — ownership check |
| Accept invitation | Invitee check | N/A | Not RBAC — creates membership via `RBACService.create_membership()` |
| Reject invitation | Invitee check | N/A | Not RBAC |

**Critical integration point:** When an invitation is accepted, the outcome handler calls:

```python
RBACService.create_membership(
    user=invitee,
    account_type=invitation.account_type,
    account_id=invitation.account_id,
    role_id=invitation.role_id,  # May be None → falls back to Base Member
    created_by=invitation.created_by,
    request=request,
)
```

### 5.2 Membership Request Flow

| Action | Permission Needed | Scope |
|--------|-------------------|-------|
| Request to join business | Any authenticated user | N/A |
| Approve membership request | `can_approve_membership_request` | business |
| Reject membership request | `can_approve_membership_request` | business |
| View pending requests | `can_approve_membership_request` | business |

### 5.3 Ownership Transfer Flow

| Action | Permission Needed | Scope | Notes |
|--------|-------------------|-------|-------|
| Initiate ownership transfer | `is_owner` check | N/A | Only owner can initiate |
| Accept ownership transfer | Target user check | N/A | Only the nominated user |
| Force ownership transfer (platform) | `can_transfer_business_ownership` | global_only | Platform override |

**Integration point:** The `OwnershipTransferOutcomeHandler` will call `RBACService.transfer_ownership()` (currently a stub that raises `NotImplementedError`).

### 5.4 New Permissions Needed

| Code | Name | Category | Scopes | Rationale |
|------|------|----------|--------|-----------|
| `can_cancel_invitation` | Cancel Invitation | invitation | business, platform_only | Cancel any pending invitation (not just your own) |
| `can_view_invitations` | View Invitations | invitation | business, platform_only | View all pending invitations for the account |
| `can_view_membership_requests` | View Membership Requests | invitation | business, platform_only | Separate from approve — view-only access |

**Decision point:** You may decide that `can_invite_member` is sufficient for viewing/canceling invitations (same permission, different action). If so, no new permissions are needed. But if you want finer granularity (e.g., an Admin role that can view invitations but not send new ones), add these.

---

## 6. Form Builder System Integration

The Form Builder has 6 permissions already defined in the registry. The integration work is consuming them.

### 6.1 Form CRUD

| Action | Permission Needed | Scope | Notes |
|--------|-------------------|-------|-------|
| Create form for business | `can_create_form` | business | |
| Create form for platform | `can_create_form` | platform_only | |
| Edit own business form | `can_edit_form` | business | |
| Edit any business form (platform) | `can_edit_form` | global_only | Platform moderating business forms |
| Delete form | `can_delete_form` | business, global_only | Same pattern |
| View form (public) | No permission | N/A | Public forms are open |
| View form (internal) | Membership check | N/A | Must be member of account |

### 6.2 Response Management

| Action | Permission Needed | Scope |
|--------|-------------------|-------|
| Submit response | Depends on form config | N/A |
| View responses | `can_view_responses` | business, global_only |
| Export responses | `can_export_responses` | business, global_only |
| Process/handle response | `can_process_response` | business, global_only |

### 6.3 Implementation Pattern

```python
# In apps/forms/services.py

class FormService:
    @staticmethod
    @transaction.atomic
    def create_form(
        *,
        account_type: str,
        account_id: UUID,
        actor_context: ActorContext,
        form_data: dict,
        request=None
    ) -> Form:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,
            required_permission="can_create_form",
        )
        # ... create form ...
```

### 6.4 New Permissions Needed: NONE

All 6 Form Builder permissions already exist.

---

## 7. Content System Integration (Future)

A social-media-like content system: posts, comments, reactions, feeds.

### 7.1 Predicted Actions

| Action | Who | Permission | Scope | Rationale |
|--------|-----|-----------|-------|-----------|
| Create post in business | Business members with perm | `can_create_post` | business | Not every member should post |
| Edit own post | Post author | Author check, no perm | N/A | Self-action |
| Edit any post in business | Business Admin+ | `can_edit_post` | business | Moderation |
| Delete own post | Post author | Author check | N/A | Self-action |
| Delete any post in business | Business Admin+ | `can_delete_post` | business | Moderation |
| Delete any post (platform) | Global Moderator+ | `can_delete_post` | global_only | Platform moderation |
| Pin/feature post | Business Admin+ | `can_manage_post` | business | Content curation |
| Create comment | Any business member | Membership check | N/A | Low barrier |
| Delete any comment | Business Admin+ | `can_moderate_comments` | business, global_only | Moderation |
| React to content | Any business member | Membership check | N/A | Low barrier |
| View feed | Any business member | Membership check | N/A | |
| View all content (platform) | Platform staff | `can_view_all_content` | global_only | Platform oversight |

### 7.2 New Permissions Needed

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_create_post` | Create Post | content | business |
| `can_edit_post` | Edit Post | content | business, global_only |
| `can_delete_post` | Delete Post | content | business, global_only |
| `can_manage_post` | Manage Post | content | business | (pin, feature, archive) |
| `can_moderate_comments` | Moderate Comments | content | business, global_only |
| `can_view_all_content` | View All Content | content | global_only, platform_only |

### 7.3 Scope Decisions

Posts and comments are **author-owned but account-scoped**. This means:

- Authors can always edit/delete their own content (no permission needed — author check)
- Business Admins can moderate within their business (business scope)
- Platform Global Moderators can moderate across all businesses (global_only scope)
- Creating posts requires explicit permission because not all members should post (e.g., a "Viewer" role)

### 7.4 Role Seeding Impact

| Role | Gets Content Permissions? | Which Ones? |
|------|--------------------------|-------------|
| Business Owner | All 6 (business scope) | Automatic — seeds all business-scope perms |
| Business Admin (custom L2) | `can_create_post`, `can_edit_post`, `can_delete_post`, `can_moderate_comments`, `can_manage_post` | Must be manually assigned when role is created |
| Business Editor (custom L5) | `can_create_post`, `can_edit_post` | Must be manually assigned |
| Base Member | None by default | Owner can grant `can_create_post` if desired |
| Platform Owner | All (broadest scope) | Automatic |
| Global Moderator | `can_edit_post`, `can_delete_post`, `can_moderate_comments`, `can_view_all_content` (global_only) | Automatic via initialization |

---

## 8. Notification System Integration (Future)

Notifications are typically low-auth — most are read-only. But notification preferences and admin controls need RBAC.

### 8.1 Predicted Actions

| Action | Who | Permission | Scope |
|--------|-----|-----------|-------|
| View own notifications | Any authenticated user | User-level, no RBAC | N/A |
| Mark own as read | User | User-level | N/A |
| Configure own preferences | User | User-level | N/A |
| Configure business notification settings | Business Admin+ | `can_edit_business` | business |
| Send announcement to all members | Business Admin+ | `can_send_announcement` | business |
| Send platform-wide announcement | Platform Admin+ | `can_send_announcement` | platform_only |
| View notification analytics | Business Admin+ | `can_view_notification_analytics` | business, platform_only |

### 8.2 New Permissions Needed

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_send_announcement` | Send Announcement | notifications | business, platform_only |
| `can_view_notification_analytics` | View Notification Analytics | notifications | business, platform_only |

**Note:** Most notification actions are user-level (no account context, no RBAC). Only admin-facing features need permissions. Reuse `can_edit_business` for notification settings rather than creating a separate permission.

---

## 9. Messaging / Chat System Integration (Future)

Direct messaging and group chat between members.

### 9.1 Predicted Actions

| Action | Who | Permission | Scope |
|--------|-----|-----------|-------|
| Send DM to business member | Any business member | Membership check | N/A |
| Create group chat | Business members with perm | `can_create_group_chat` | business |
| Manage group chat | Chat creator or Admin+ | `can_manage_group_chat` | business |
| Delete messages (moderation) | Business Admin+ | `can_moderate_messages` | business, global_only |
| View message logs (audit) | `can_view_audit_logs` | Already exists | business, platform_and_global |
| Send cross-business message | Platform staff | `can_send_cross_account_message` | global_only |

### 9.2 New Permissions Needed

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_create_group_chat` | Create Group Chat | messaging | business |
| `can_manage_group_chat` | Manage Group Chat | messaging | business |
| `can_moderate_messages` | Moderate Messages | messaging | business, global_only |
| `can_send_cross_account_message` | Send Cross-Account Message | messaging | global_only |

### 9.3 Special Consideration: Suspended Members

When a member is suspended, they should not be able to send messages. This is already handled by the RBAC system: `build_actor_context()` raises `PermissionDenied` for non-active memberships. If your chat system checks membership status before allowing messages, suspended members are automatically blocked.

---

## 10. Analytics / Reporting System Integration (Future)

Business analytics, platform metrics, reporting dashboards.

### 10.1 Predicted Actions

| Action | Who | Permission | Scope |
|--------|-----|-----------|-------|
| View business dashboard | Business members with perm | `can_view_analytics` | business |
| View detailed reports | Business Admin+ | `can_view_reports` | business |
| Export reports | Business Admin+ | `can_export_reports` | business |
| View platform-wide metrics | Platform staff | `can_view_platform_analytics` | platform_only |
| View cross-business comparisons | Platform Admin+ | `can_view_platform_analytics` | platform_only, global_only |

### 10.2 New Permissions Needed

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_view_analytics` | View Analytics | analytics | business, platform_only |
| `can_view_reports` | View Reports | analytics | business, platform_only |
| `can_export_reports` | Export Reports | analytics | business, platform_only |
| `can_view_platform_analytics` | View Platform Analytics | analytics | platform_only, global_only |

---

## 11. Billing / Subscription System Integration (Future)

Business subscriptions, payment methods, invoices.

### 11.1 Predicted Actions

| Action | Who | Permission | Scope |
|--------|-----|-----------|-------|
| View billing info | Business Owner or members with perm | `can_view_billing` | business |
| Manage payment methods | Business Owner or members with perm | `can_manage_billing` | business |
| Change subscription plan | Business Owner only | `is_owner` check | N/A |
| View invoices | Business members with perm | `can_view_billing` | business |
| Issue refund (platform) | Platform Admin+ | `can_manage_platform_billing` | platform_only |
| Override billing (platform) | Platform Owner | `can_manage_platform_billing` | platform_only |

### 11.2 New Permissions Needed

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_view_billing` | View Billing | billing | business |
| `can_manage_billing` | Manage Billing | billing | business |
| `can_manage_platform_billing` | Manage Platform Billing | billing | platform_only |

### 11.3 Special Consideration: Owner-Only Actions

Changing the subscription plan should be Owner-only, NOT permission-based. This is a critical business decision that should not be delegatable. Use `is_owner` check, not a permission:

```python
if not actor_context.is_owner:
    raise PermissionDenied(message="Only the account owner can change the subscription plan")
```

---

## 12. File / Media Management Integration (Future)

File uploads, media library, document storage.

### 12.1 Predicted Actions

| Action | Who | Permission | Scope |
|--------|-----|-----------|-------|
| Upload file to business | Business members with perm | `can_upload_media` | business |
| Delete any file in business | Business Admin+ | `can_manage_media` | business |
| Delete own file | File owner | Author check | N/A |
| View media library | Any business member | Membership check | N/A |
| Set storage limits (platform) | Platform Admin+ | `can_manage_platform_settings` | platform_only |
| Delete media across businesses | Global Moderator+ | `can_manage_media` | global_only |

### 12.2 New Permissions Needed

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_upload_media` | Upload Media | media | business |
| `can_manage_media` | Manage Media | media | business, global_only |

---

## 13. Permission Registry Evolution Plan

### Current State (25 permissions)

```
membership (7) · roles (3) · settings (3) · platform (6) · audit (1) · forms (6)
```

### After Content System (~31 permissions)

```
+ content (6): create_post, edit_post, delete_post, manage_post,
               moderate_comments, view_all_content
```

### After Notification System (~33 permissions)

```
+ notifications (2): send_announcement, view_notification_analytics
```

### After Messaging System (~37 permissions)

```
+ messaging (4): create_group_chat, manage_group_chat,
                  moderate_messages, send_cross_account_message
```

### After Analytics System (~41 permissions)

```
+ analytics (4): view_analytics, view_reports, export_reports,
                  view_platform_analytics
```

### After Billing System (~44 permissions)

```
+ billing (3): view_billing, manage_billing, manage_platform_billing
```

### After Media System (~46 permissions)

```
+ media (2): upload_media, manage_media
```

### Projected Final State: ~46 permissions across 12 categories

This is well within a manageable range. Each category stays at 2-7 permissions, keeping the system comprehensible.

---

## 14. Migration Strategy

### How To Add New Permissions

**Step 1:** Add to `permissions/registry.py`:

```python
# In PERMISSIONS list, add:
(
    "can_create_post",
    "Create Post",
    "Create new posts in the account",
    "content",
    ["business"],
),
```

**Step 2:** Create a new data migration:

```python
# apps/rbac/migrations/000X_seed_content_permissions.py

from django.db import migrations

CONTENT_PERMISSIONS = [
    ("can_create_post", "Create Post", "Create new posts", "content", ["business"]),
    ("can_edit_post", "Edit Post", "Edit existing posts", "content", ["business", "global_only"]),
    # ... etc
]

def seed_content_permissions(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    for code, name, description, category, applicable_scopes in CONTENT_PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': description,
                'category': category,
                'applicable_scopes': applicable_scopes,
            }
        )

def reverse_content_permissions(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    codes = [p[0] for p in CONTENT_PERMISSIONS]
    Permission.objects.filter(code__in=codes).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('rbac', '000X_previous'),  # Last RBAC migration
    ]
    operations = [
        migrations.RunPython(seed_content_permissions, reverse_content_permissions),
    ]
```

**Step 3:** Run `python manage.py migrate`

### What Happens Automatically

After migration, the new permissions exist in the `Permission` table. The next time `initialize_business_account()` is called for a NEW business, the Owner role will automatically get all permissions with `"business"` in their `applicable_scopes`. Similarly, `initialize_platform_account()` will automatically pick up new platform/global permissions.

### What Does NOT Happen Automatically

**Existing businesses do NOT get new permissions on their Owner roles.** You need a one-time data migration to add new permissions to existing Owner roles:

```python
# 000X_backfill_content_permissions_to_existing_owners.py

def backfill(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Role = apps.get_model('rbac', 'Role')
    RolePermission = apps.get_model('rbac', 'RolePermission')

    # Get all new content permissions
    content_perms = Permission.objects.filter(category='content')

    # Get all existing Business Owner roles
    owner_roles = Role.objects.filter(
        account_type='business',
        level=0,
        is_system_role=True,
    )

    for role in owner_roles:
        for perm in content_perms:
            if 'business' in (perm.applicable_scopes or []):
                RolePermission.objects.get_or_create(
                    role=role,
                    permission=perm,
                    defaults={'scope': 'business'},
                )
```

**Existing Platform roles also need backfilling** if you add permissions with `platform_only` or `global_only` scopes. Apply the same pattern for Platform Admin and Global Moderator roles.

---

## 15. Patterns & Anti-Patterns

### ✅ Pattern 1: Service-Level Authorization

Always check permissions in the service layer, never in views.

```python
# ✅ CORRECT — service handles authorization
class PostService:
    @staticmethod
    def create_post(*, actor_context, business_id, content, request=None):
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,
            required_permission="can_create_post",
        )
        # ... create post ...

# In view:
class BusinessPostCreateView(BusinessContextMixin, APIView):
    def post(self, request, business_slug):
        actor_context = self.get_actor_context()
        post = PostService.create_post(
            actor_context=actor_context,
            business_id=self.get_account_id(),
            content=request.data,
            request=request,
        )
```

### ❌ Anti-Pattern 1: View-Level Permission Checks

```python
# ❌ WRONG — authorization in view, not service
class BusinessPostCreateView(BusinessContextMixin, APIView):
    def post(self, request, business_slug):
        actor_context = self.get_actor_context()
        if not actor_context.has_permission("can_create_post"):
            raise PermissionDenied(...)
        PostService.create_post(content=request.data)  # Service has no auth check
```

This is dangerous because another caller (e.g., an API, a Celery task, another service) could bypass the view and call `PostService.create_post()` without authorization.

### ✅ Pattern 2: Author + Permission Dual Check

For content owned by users (posts, comments, files), use a two-tier check:

```python
# Author can always edit their own content
# Others need the moderation permission
def edit_post(*, actor_context, post, changes, request=None):
    if post.author_id != actor_context.user_id:
        # Not the author — need moderation permission
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,
            required_permission="can_edit_post",
        )
    # ... apply changes ...
```

### ✅ Pattern 3: Membership Check Without Permission

For actions that require being a member but no specific permission (e.g., viewing a business feed, reacting to content):

```python
# ✅ Just verify membership exists — no permission needed
membership = MembershipSelector.get_active_membership_for_user_account(
    user=request.user,
    account_type=AccountType.BUSINESS,
    account_id=business.id,
)
if not membership:
    raise PermissionDenied(message="You are not a member of this business")
```

### ✅ Pattern 4: Owner-Only Actions

For critical business decisions (delete business, change plan, transfer ownership):

```python
# ✅ Use is_owner flag, NOT a permission
if not actor_context.is_owner:
    raise PermissionDenied(message="Only the account owner can perform this action")
```

**Why not a permission?** Owner-only actions are non-delegatable by design. If you make them permission-based, the owner could assign the permission to an Admin, which undermines the safety model.

### ❌ Anti-Pattern 2: Checking Role Name

```python
# ❌ WRONG — checking role name instead of permission
if actor_context.role_name != "Admin":
    raise PermissionDenied(...)
```

Role names are display strings. Custom roles can have any name. Always check permissions or role level.

### ❌ Anti-Pattern 3: Skipping ActorContext

```python
# ❌ WRONG — manually constructing permission checks
user_perms = RolePermission.objects.filter(role__memberships__user=user)
if not user_perms.filter(permission__code="can_edit_post").exists():
    raise PermissionDenied(...)
```

Always go through `RBACService.build_actor_context()` → `MembershipPolicy.authorize_action()`. The ActorContext captures the point-in-time snapshot, handles scope resolution, and ensures caching works.

### ✅ Pattern 5: Cross-Account Moderation

When platform staff act on business content:

```python
def delete_post_cross_account(*, actor_context, post, request=None):
    # Get the post author's membership to use as target
    author_membership = MembershipSelector.get_membership_for_user_account(
        user_id=post.author_id,
        account_type=AccountType.BUSINESS,
        account_id=post.business_id,
    )

    # This will check global scope because actor is platform, target is business
    MembershipPolicy.authorize_action(
        actor_context=actor_context,
        target_membership=author_membership,  # or None if no target-member check needed
        required_permission="can_delete_post",
    )
```

**Important:** For content moderation where you don't need to check dominance against a specific member (you just want to verify the actor has the global permission), you can pass `target_membership=None`. The cross-account scope check still happens based on `actor_context.account_type` vs the business being moderated. You would need to create a synthetic "account context check" or simply use `actor_context.has_global_permission("can_delete_post")` directly for simpler cases.

---

## 16. Role Seeding Updates

When new permissions are added, the default role seeding logic in `initialize_*_account()` handles most cases automatically. Here's what each role gets:

### Business Roles (Automatic)

| Role | What It Gets | How |
|------|-------------|-----|
| Owner (L0) | ALL permissions with `"business"` in applicable_scopes | `PermissionSelector.get_permissions_by_scope(scope="business")` |
| Base Member (L10) | Zero permissions | No seeding |

**Custom roles** (Admin, Editor, etc.) are created by the Business Owner and manually assigned permissions. The system doesn't auto-seed custom roles.

### Platform Roles (Automatic)

| Role | What It Gets | How |
|------|-------------|-----|
| Platform Owner (L0) | ALL permissions with broadest scope | Iterates all perms, picks `p_and_g > global > platform > business` |
| Platform Admin (L2) | All permissions with `"platform_only"` in applicable_scopes | `get_permissions_by_scope(scope="platform_only")` |
| Global Moderator (L5) | All permissions with `"global_only"` in applicable_scopes | `get_permissions_by_scope(scope="global_only")` |

### What This Means For New Permissions

If you add `can_create_post` with `applicable_scopes=["business"]`:

- Business Owner: ✅ Gets it automatically on next `initialize_business_account()`
- Platform Owner: ✅ Gets it automatically (with `business` scope, since no broader scope applies)
- Platform Admin: ❌ Does NOT get it (no `platform_only` in scopes)
- Global Moderator: ❌ Does NOT get it (no `global_only` in scopes)

If you add `can_delete_post` with `applicable_scopes=["business", "global_only"]`:

- Business Owner: ✅ Gets it with `business` scope
- Platform Owner: ✅ Gets it with `global_only` scope
- Platform Admin: ❌ Does NOT get it
- Global Moderator: ✅ Gets it with `global_only` scope

---

## 17. Testing Strategy for New Integrations

For every new app that integrates with RBAC, write these test categories:

### Category 1: Permission-Required Tests

Test that the service method requires the permission and rejects without it.

```python
def test_create_post_requires_permission(self):
    """Member without can_create_post cannot create posts."""
    actor = build_actor_context(permissions=[])  # No permissions
    with pytest.raises(PermissionDenied):
        PostService.create_post(actor_context=actor, ...)

def test_create_post_with_permission(self):
    """Member with can_create_post can create posts."""
    actor = build_actor_context(permissions=[("can_create_post", "business")])
    post = PostService.create_post(actor_context=actor, ...)
    assert post is not None
```

### Category 2: Scope Boundary Tests

Test that business scope cannot cross accounts.

```python
def test_business_admin_cannot_delete_post_in_other_business(self):
    """Business Admin in Business A cannot delete post in Business B."""
    admin_a = build_actor_context(
        account_id=business_a.id,
        permissions=[("can_delete_post", "business")]
    )
    post_in_b = PostFactory(business=business_b)
    with pytest.raises(PermissionDenied):
        PostService.delete_post(actor_context=admin_a, post=post_in_b)
```

### Category 3: Cross-Account Moderation Tests

Test that global scope works cross-account.

```python
def test_global_moderator_can_delete_post_in_business(self):
    """Global Moderator can delete any business post."""
    moderator = build_actor_context(
        account_type=AccountType.PLATFORM,
        permissions=[("can_delete_post", "global_only")]
    )
    post = PostFactory(business=some_business)
    PostService.delete_post(actor_context=moderator, post=post)
    assert post.is_deleted
```

### Category 4: Author Self-Action Tests

```python
def test_author_can_edit_own_post_without_permission(self):
    """Post author can edit their own post even without can_edit_post."""
    author_actor = build_actor_context(user_id=author.id, permissions=[])
    post = PostFactory(author=author)
    PostService.edit_post(actor_context=author_actor, post=post, changes={...})
```

### Category 5: Audit Trail Tests

```python
@mock.patch('apps.content.services.AuditService.log')
def test_delete_post_audited(self, mock_log):
    PostService.delete_post(actor_context=admin_actor, post=post)
    mock_log.assert_called_once()
    assert mock_log.call_args.kwargs['action'] == AuditLog.Action.POST_DELETED
```

---

*End of RBAC Integration Playbook*
