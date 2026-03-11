# Member Quota System — Implementation Plan

**Date**: 2026-03-04
**Scope**: Cross-app (Organization, RBAC, Transaction, Frontend)
**Estimated**: ~11 backend files, ~8 frontend files, 1 migration, ~15 new tests

---

## Context

Businesses and platform accounts can have members/roles via the RBAC system. Currently there are no limits on member count. This plan adds a **quota-based gating system**:

- **Business accounts**: default `max_members=1` (owner only). Superuser can raise it (e.g., to 6) to enable team features.
- **Platform account**: default `max_members=5` (singleton).
- `max_members=0` means unlimited (future use).
- When `max_members=1`, the frontend hides Members/Roles nav items (owner-only account, no team UI).

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single `PositiveSmallIntegerField` per account | No boolean flags, no singleton config table — simple, extensible |
| Two enforcement points: hard gate + UX pre-check | Safety net at `create_membership()` + early rejection at invitation/request creation |
| `initialize_business_account()` bypasses quota | Owner is always slot #1, created via `Membership.objects.create()` directly |
| `BusinessRuleViolation` exception | Consistent with existing domain exceptions, rule=`"member_quota_exceeded"` |
| `max_members` read-only in API | Admin-only field — NOT in `BusinessUpdateInput` or `BusinessCreateInput` |
| `account_max_members` in membership serializer | Enables frontend nav filtering without extra API calls |
| Factory default `max_members=6` | Test convenience — most tests need members, quota tests use explicit values |

---

## Step 1: Model Layer

### 1a. BusinessAccount — add field
**File**: `backend/apps/organization/business/models.py`

Add after `is_platform_branch` field (~line 43):
```python
max_members = models.PositiveSmallIntegerField(
    default=1,
    help_text="Maximum number of members allowed. 0 = unlimited.",
)
```

### 1b. PlatformAccount — add field
**File**: `backend/apps/organization/platform/models.py`

Add after `is_configured` field (~line 14):
```python
max_members = models.PositiveSmallIntegerField(
    default=5,
    help_text="Maximum number of members allowed. 0 = unlimited.",
)
```

---

## Step 2: Migration

Single migration for both models (same `organization` app):
```
python manage.py makemigrations organization
```
Produces one migration adding `max_members` to `business_account` and `platform_account` tables.

---

## Step 3: RBAC Service — Hard Gate

The single funnel for ALL membership creation (invitations accepted, requests approved).

### 3a. Add `MembershipSelector.count_active_members()`
**File**: `backend/apps/rbac/selectors.py`

```python
@staticmethod
def count_active_members(*, account_type: str, account_id: UUID) -> int:
    """Count active (non-deleted) members in an account."""
    return Membership.objects.active().filter(
        account_type=account_type,
        account_id=account_id,
    ).count()
```

### 3b. Quota check in `create_membership()`
**File**: `backend/apps/rbac/services.py` — insert before existing membership check (~line 326)

```python
# Quota enforcement
active_count = MembershipSelector.count_active_members(
    account_type=account_type, account_id=account_id,
)
if account_type == AccountType.BUSINESS:
    from apps.organization.business.models import BusinessAccount
    max_members = BusinessAccount.objects.values_list(
        "max_members", flat=True
    ).get(id=account_id)
elif account_type == AccountType.PLATFORM:
    from apps.organization.platform.models import PlatformAccount
    max_members = PlatformAccount.objects.values_list(
        "max_members", flat=True
    ).get(id=account_id)
else:
    max_members = 0

if max_members > 0 and active_count >= max_members:
    raise BusinessRuleViolation(
        message=f"Account has reached its maximum member limit ({max_members})",
        rule="member_quota_exceeded",
    )
```

**Why `values_list().get()`**: Avoids loading full model — only need the integer. Uses lazy imports (existing codebase pattern).

---

## Step 4: Transaction Service — UX Pre-checks

Convenience checks that prevent creating futile transactions. Hard gate in Step 3 is safety net.

### 4a. Private helper `_check_member_quota()`
**File**: `backend/apps/transaction/services.py` — add as `@staticmethod`

```python
@staticmethod
def _check_member_quota(*, account_type: str, account_id: UUID):
    """Pre-check: raise if account is at member capacity."""
    from apps.rbac.selectors import MembershipSelector
    active_count = MembershipSelector.count_active_members(
        account_type=account_type, account_id=account_id,
    )
    if account_type == ContextType.BUSINESS:
        from apps.organization.business.models import BusinessAccount
        max_members = BusinessAccount.objects.values_list(
            "max_members", flat=True
        ).get(id=account_id)
    elif account_type == ContextType.PLATFORM:
        from apps.organization.platform.models import PlatformAccount
        max_members = PlatformAccount.objects.values_list(
            "max_members", flat=True
        ).get(id=account_id)
    else:
        return

    if max_members > 0 and active_count >= max_members:
        raise BusinessRuleViolation(
            message=f"Account has reached its maximum member limit ({max_members})",
            rule="member_quota_exceeded",
        )
```

### 4b. In `create_invitation()` — after existing membership check (~line 94)
```python
# Quota pre-check for membership invitations
if is_membership_invitation and config.context_type not in ("user", None):
    TransactionService._check_member_quota(
        account_type=config.context_type,
        account_id=initiator_context.account_id,
    )
```

### 4c. In `create_request()` — after cooldown check (~line 228)
```python
# Quota pre-check for membership requests
is_membership_request = "MembershipOutcomeHandler.handle_request_approved" in (
    config.outcome_handler or ""
)
if is_membership_request and config.context_type not in ("user", None):
    context_id = target_account_id if config.context_type != "user" else None
    if context_id:
        TransactionService._check_member_quota(
            account_type=config.context_type,
            account_id=context_id,
        )
```

---

## Step 5: Serializers

### 5a. BusinessAccountOutput — add `max_members`
**File**: `backend/apps/organization/business/serializers.py`
Add `"max_members"` to `BusinessAccountOutput.Meta.fields` list.

### 5b. BusinessAccountListOutput — add `max_members`
Same file, add `"max_members"` to `BusinessAccountListOutput.Meta.fields` list.

### 5c. PlatformAccountOutput — add `max_members`
**File**: `backend/apps/organization/platform/serializers.py`
Add `"max_members"` to `PlatformAccountOutput.Meta.fields` list.

### 5d. MyMembershipOutputSerializer — add `account_max_members`
**File**: `backend/apps/rbac/serializers.py`

```python
account_max_members = serializers.SerializerMethodField()

# Add "account_max_members" to Meta.fields

def get_account_max_members(self, obj) -> int:
    """Return max_members for the account this membership belongs to."""
    if obj.account_type == AccountType.BUSINESS:
        from apps.organization.business.models import BusinessAccount
        try:
            return BusinessAccount.objects.values_list(
                "max_members", flat=True
            ).get(id=obj.account_id)
        except BusinessAccount.DoesNotExist:
            return 0
    elif obj.account_type == AccountType.PLATFORM:
        from apps.organization.platform.models import PlatformAccount
        try:
            return PlatformAccount.objects.values_list(
                "max_members", flat=True
            ).get(id=obj.account_id)
        except PlatformAccount.DoesNotExist:
            return 0
    return 0
```

---

## Step 6: Admin Panel

### 6a. BusinessAccountAdmin
**File**: `backend/apps/organization/business/admin.py`
- Add `"max_members"` to `list_display` (after `verification_status`)
- Add `"max_members"` to `list_filter`
- Add `"max_members"` to `list_editable`
- Add bulk actions:
```python
@admin.action(description="Enable team membership (max_members=6)")
def enable_team_membership(self, request, queryset):
    updated = queryset.update(max_members=6)
    self.message_user(request, f"{updated} businesses updated to max_members=6.")

@admin.action(description="Disable team membership (max_members=1)")
def disable_team_membership(self, request, queryset):
    updated = queryset.update(max_members=1)
    self.message_user(request, f"{updated} businesses set to owner-only (max_members=1).")
```

### 6b. PlatformAccountAdmin
**File**: `backend/apps/organization/platform/admin.py`
- Add `"max_members"` to `list_display`
- Add `"max_members"` to the detail fieldset (not list_editable — singleton)

---

## Step 7: Frontend Types

### 7a. Organization types
**File**: `frontend/src/types/organization.ts`
- Add `max_members: number;` to `BusinessAccount` (after `is_platform_branch`)
- Add `max_members: number;` to `BusinessAccountList` (after `is_platform_branch`)
- Add `max_members: number;` to `PlatformAccount` (after `is_configured`)

### 7b. RBAC types
**File**: `frontend/src/types/rbac.ts`
- Add `account_max_members: number;` to `Membership` (after `permissions`)

### 7c. Navigation types
**File**: `frontend/src/types/navigation.ts`
- Add to `NavItem` (after `ownerOnly?`):
```typescript
/** Minimum max_members required for this item to be visible. Omit = always visible */
minMembers?: number;
```

---

## Step 8: Frontend Navigation

### 8a. Navigation config — add minMembers gates
**File**: `frontend/src/lib/navigation-config.ts`
- `biz-members`: add `minMembers: 2`
- `biz-roles`: add `minMembers: 2`
- `plat-members`: add `minMembers: 2`
- `plat-roles`: add `minMembers: 2`

### 8b. useFilteredNav — add minMembers filter
**File**: `frontend/src/hooks/use-filtered-nav.ts`
Add filter in `items.filter()` callback (~line 44):
```typescript
if (item.minMembers && membership.account_max_members < item.minMembers) return false;
```

---

## Step 9: Backend Tests — New Quota Tests

### 9a. RBAC Service quota tests
**File**: `backend/apps/rbac/tests/test_services.py` — new class `TestCreateMembershipQuota`

| Test | Scenario |
|------|----------|
| `test_blocked_when_business_at_quota` | max_members=1, owner exists → BusinessRuleViolation |
| `test_allowed_when_business_below_quota` | max_members=6, 1 owner → succeeds |
| `test_blocked_when_exactly_at_quota` | max_members=2, 2 members → BusinessRuleViolation |
| `test_unlimited_when_zero` | max_members=0 → always succeeds |
| `test_blocked_when_platform_at_quota` | platform max_members=2, 2 members → blocked |
| `test_allowed_when_platform_below_quota` | platform max_members=5, 1 member → succeeds |

### 9b. MembershipSelector count test
**File**: `backend/apps/rbac/tests/test_selectors.py`

| Test | Scenario |
|------|----------|
| `test_count_active_members` | 3 active + 1 suspended → returns 3 |

### 9c. Transaction Service pre-check tests
**File**: `backend/apps/transaction/tests/test_services.py` — new class `TestMemberQuotaPreCheck`

| Test | Scenario |
|------|----------|
| `test_invitation_blocked_at_quota` | business max_members=1, owner exists → BusinessRuleViolation |
| `test_invitation_allowed_below_quota` | business max_members=6 → succeeds |
| `test_request_blocked_at_quota` | business max_members=1 → BusinessRuleViolation |
| `test_request_allowed_below_quota` | business max_members=6 → succeeds |

### 9d. Serializer field presence tests
- BusinessAccountOutput: assert `max_members` in GET response
- PlatformAccountOutput: assert `max_members` in GET response
- MyMembershipOutput: assert `account_max_members` in response

---

## Step 10: Frontend Tests — Updates

### 10a. use-filtered-nav.test.ts — add minMembers test
**File**: `frontend/src/hooks/use-filtered-nav.test.ts`

```typescript
it("hides items with minMembers when account_max_members is below threshold", () => {
  mockUsePathname.mockReturnValue("/bconsole/acme/dashboard");
  useMembershipStore.setState({
    memberships: [
      makeMembership({
        account_max_members: 1,
        permissions: makePermissions("can_view_members", "can_create_role"),
      }),
    ],
    isLoaded: true,
  });
  const { result } = renderHook(() => useFilteredNav());
  const allItems = result.current.flatMap((s) => s.items);
  const keys = allItems.map((i) => i.key);
  expect(keys).not.toContain("biz-members");
  expect(keys).not.toContain("biz-roles");
  expect(keys).toContain("biz-dashboard");
});
```

### 10b. Mock data updates
- `business-api.test.ts` — add `max_members` to mock BusinessAccount/List
- `platform-api.test.ts` — add `max_members` to mock PlatformAccount
- `use-filtered-nav.test.ts` — add `account_max_members` to `makeMembership()` helper

---

## Step 11: Factory Updates (Test Stability)

### 11a. BusinessAccountFactory — add max_members=6
**File**: `backend/apps/organization/tests/factories.py`
```python
max_members = 6  # Test convenience (production default is 1)
```

### 11b. PlatformAccountFactory — add max_members=5
**File**: `backend/apps/organization/tests/factories.py`
Also update: `backend/apps/rbac/tests/factories.py` (has own PlatformAccountFactory)
```python
max_members = 5  # Matches production default
```

---

## Files Modified Summary

### Backend (11 files + 1 migration)
| File | Change |
|------|--------|
| `apps/organization/business/models.py` | Add `max_members` field |
| `apps/organization/platform/models.py` | Add `max_members` field |
| `apps/organization/business/serializers.py` | Add to output fields |
| `apps/organization/platform/serializers.py` | Add to output fields |
| `apps/organization/business/admin.py` | list_display, list_filter, list_editable, bulk actions |
| `apps/organization/platform/admin.py` | list_display, fieldset |
| `apps/rbac/services.py` | Quota check in `create_membership()` |
| `apps/rbac/selectors.py` | Add `count_active_members()` |
| `apps/rbac/serializers.py` | Add `account_max_members` to MyMembership |
| `apps/transaction/services.py` | `_check_member_quota()` + pre-checks in create_invitation/request |
| `apps/organization/tests/factories.py` | Factory defaults |
| `apps/rbac/tests/factories.py` | PlatformAccountFactory default |

### Frontend (8 files)
| File | Change |
|------|--------|
| `src/types/organization.ts` | Add `max_members` to 3 interfaces |
| `src/types/rbac.ts` | Add `account_max_members` to Membership |
| `src/types/navigation.ts` | Add `minMembers?` to NavItem |
| `src/lib/navigation-config.ts` | Add `minMembers: 2` to 4 items |
| `src/hooks/use-filtered-nav.ts` | Add minMembers filter |
| `src/hooks/use-filtered-nav.test.ts` | Add test + update mock |
| `src/features/business/api/business-api.test.ts` | Update mock data |
| `src/features/platform/api/platform-api.test.ts` | Update mock data |

---

## Race Condition Analysis

**Scenario**: max_members=6, 5 active, 2 invitations sent. Both accepted simultaneously.

1. First accept → `create_membership()` → 5 < 6 → **succeeds** (now 6)
2. Second accept → `create_membership()` → 6 >= 6 → **BusinessRuleViolation**
3. `accept()` is `@db_transaction.atomic` + `_execute_outcome()` re-raises → **entire accept rolls back**
4. Transaction stays PENDING, user sees error, can retry if spot opens

**Result**: Safe. No data corruption.

---

## Existing Test Stability

Transaction tests use `MembershipFactory` (direct `Membership.objects.create()`) bypassing quota check. But `count_active_members()` counts all active members. With factory default `max_members=6`, existing tests (1-3 members) are safe.

**Affected files (all safe with factory default=6):**
- `apps/rbac/tests/test_services.py` — calls `create_membership()` service
- `apps/rbac/tests/test_actor_scenarios.py` — calls `create_membership()` service
- `apps/transaction/tests/test_services.py` — calls `create_invitation()` / `create_request()`
- `apps/transaction/tests/test_outcome_handlers.py` — mocks `create_membership()`, no impact
- `apps/organization/tests/conftest.py` — `member_user` fixture calls `create_membership()`

---

## What NOT to Touch

| Component | Reason |
|-----------|--------|
| `RBACService.initialize_business_account()` | Owner created via `Membership.objects.create()` — bypasses service quota by design |
| `RBACService.initialize_platform_account()` | Creates roles only, no membership |
| `TransactionService.accept()` / `deny()` / `cancel()` | No changes needed |
| `RBACService.transfer_ownership()` | Swaps roles, doesn't change member count |
| `RBACService.member_leave()` / `update_membership_status()` | Reduces/freezes count, no quota issue |
| `RBACService.change_member_role()` | Doesn't affect member count |
| `TransactionPolicy` | Quota != permission (different concern) |

---

## Verification Checklist

1. `python manage.py makemigrations organization && python manage.py migrate`
2. `pytest apps/rbac/ apps/transaction/ apps/organization/ -x -v` — existing + new tests pass
3. `pytest --tb=short` — all 2780+ backend tests pass (no regressions)
4. `cd frontend && npm run test` — all 539+ frontend tests pass
5. Django admin → BusinessAccount → verify max_members column, filter, inline editing, bulk actions
6. (Optional) `make test-api` — verify serializer output includes max_members
