# D13 — Audit REST API Implementation Plan

## Context

The audit system has a complete backend (model, service, selector, admin) but **zero REST API endpoints**. Decision 4 says: separate endpoints per console, shared selector. Decision 13 says: build business + platform scoped endpoints standalone now; governance-scoped added to gconsole.

This unblocks:
- `/bconsole/[slug]/audit` stub page (business-scoped)
- `/pconsole/audit` stub page (platform-scoped)
- `/gconsole/audit` page (governance-scoped, Phase 3)
- 1 deferred E2E workflow (`audit-trail-verification.spec.ts`)

## What exists

| Component | Status | Location |
|-----------|--------|----------|
| AuditLog model | Complete (100+ actions, immutable) | `apps/core/observability/audit/models.py` |
| AuditService | Complete (log, log_failure, log_change) | `apps/core/observability/audit/service.py` |
| AuditSelector | 6 query methods | `apps/core/observability/audit/selectors.py` |
| Admin | Read-only, filters, search | `apps/core/observability/admin.py` |
| Permission | `can_view_audit_logs` — scopes: business, platform_only, global_only, platform_and_global | `apps/rbac/permissions/registry.py:199-205` |
| REST endpoints | **NONE** | — |

## What we build

3 READ-ONLY endpoints with shared serializer + selector logic:

| Endpoint | Scope | Permission | Pagination | Auth |
|----------|-------|-----------|------------|------|
| `GET /api/v1/business/{slug}/audit/` | Business | `can_view_audit_logs` (business scope) | StandardPagination | IsAuthenticated |
| `GET /api/v1/platform/audit/` | Platform | `can_view_audit_logs` (platform_only scope) | StandardPagination | IsAuthenticated |
| `GET /api/v1/governance/audit/` | Global | `can_view_audit_logs` (global scope) | LargeResultsPagination | IsAuthenticated + GovernanceTokenRequired |

All endpoints are GET-only (audit logs are immutable — no POST/PATCH/DELETE).

**Pagination note:** `CursorResultsPagination` orders by `-created_at` but AuditLog uses `timestamp` (not `created_at`). Using `LargeResultsPagination` (50/page, max 200) for governance which handles large result sets. The composite index `audit_timestamp_idx` on `-timestamp` keeps page-number pagination efficient. Cursor pagination can be added later via a custom `AuditCursorPagination(ordering="-timestamp")` if governance dataset exceeds practical page limits.

### Query parameters (shared across all 3 endpoints):

| Param | Type | Description |
|-------|------|-------------|
| `action` | string | Filter by action code (e.g., `org.business.suspended`) |
| `outcome` | string | Filter by outcome (`SUCCESS`, `FAILURE`, `DENIED`) |
| `actor_id` | uuid | Filter by actor |
| `since` | ISO datetime | Filter logs after this timestamp |
| `until` | ISO datetime | Filter logs before this timestamp |
| `resource_type` | string | Filter by resource type (e.g., `BusinessAccount`) |

### Scoping logic:

- **Business-scoped**: `resource_type="BusinessAccount" AND resource_id=business.id`. Shows direct business lifecycle actions (created, updated, suspended, reactivated, archived, profile_updated, verification).
- **Platform-scoped**: Actions matching platform-related prefixes: `org.platform.*`, `rbac.*` (for platform account_type), `admin.*`, `auth.governance.*`. Shows platform configuration, RBAC changes, and governance session events.
- **Governance-scoped**: No resource filter — all audit logs accessible. Full cross-account visibility.

---

## Implementation Steps

### Step 1: Extend AuditSelector

**File:** `backend/apps/core/observability/audit/selectors.py`

Add 3 new methods:

```python
@staticmethod
def list_for_business(business_id, *, action=None, outcome=None, since=None, until=None) -> QuerySet:
    """Business-scoped audit: direct business resource actions."""
    qs = AuditLog.objects.filter(
        resource_type="BusinessAccount",
        resource_id=str(business_id),
    )
    # Apply optional filters...
    return qs.order_by("-timestamp")

@staticmethod
def list_for_platform(*, action=None, outcome=None, actor_id=None, since=None, until=None, resource_type=None) -> QuerySet:
    """Platform-scoped audit: platform-related actions."""
    from django.db.models import Q
    qs = AuditLog.objects.filter(
        Q(action__startswith="org.platform.") |
        Q(action__startswith="admin.") |
        Q(action__startswith="auth.governance.")
    )
    # Apply optional filters...
    return qs.order_by("-timestamp")

@staticmethod
def list_all(*, action=None, outcome=None, actor_id=None, since=None, until=None, resource_type=None) -> QuerySet:
    """Governance-scoped audit: all logs, no scope filter."""
    qs = AuditLog.objects.all()
    # Apply optional filters...
    return qs.order_by("-timestamp")
```

Reuse pattern from existing `get_by_actor()` (line 34) and `get_by_action()` (line 77).

Extract a shared `_apply_common_filters(qs, action, outcome, actor_id, since, until, resource_type)` helper to avoid duplication.

### Step 2: Create audit serializer

**New file:** `backend/apps/core/observability/audit/serializers.py`

```python
class AuditLogOutput(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id", "timestamp", "actor_id", "actor_email", "actor_type",
            "action", "resource_type", "resource_id", "resource_repr",
            "outcome", "details", "changes", "ip_address", "request_id",
        ]
        read_only_fields = fields  # All read-only
```

Follow `BusinessAccountListOutput` pattern (serializers.py:214-236).

### Step 3: Create audit views

**New file:** `backend/apps/core/observability/audit/views.py`

3 view classes:

```python
class BusinessAuditListView(APIView):
    """GET /api/v1/business/{slug}/audit/"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request, slug):
        # 1. Look up business by slug
        # 2. Check BusinessPolicy.can_view(user, business) or _has_business_permission("can_view_audit_logs")
        # 3. Call AuditSelector.list_for_business(business.id, **filters)
        # 4. Paginate + serialize

class PlatformAuditListView(APIView):
    """GET /api/v1/platform/audit/"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        # 1. Check PlatformPolicy._has_platform_permission("can_view_audit_logs")
        # 2. Call AuditSelector.list_for_platform(**filters)
        # 3. Paginate + serialize

class GovernanceAuditListView(APIView):
    """GET /api/v1/governance/audit/"""
    permission_classes = [IsAuthenticated, GovernanceTokenRequired]
    pagination_class = LargeResultsPagination

    def get(self, request):
        # 1. GovernanceTokenRequired already validates governance access
        # 2. Check BusinessPolicy._has_global_permission("can_view_audit_logs")
        # 3. Call AuditSelector.list_all(**filters)
        # 4. Paginate + serialize
```

Extract a shared `_extract_audit_filters(request)` helper to parse query params consistently.

### Step 4: Register URLs

**Business audit** — add to `backend/apps/organization/business/urls.py`:
```python
path("<slug:slug>/audit/", AuditBusinessView.as_view(), name="business-audit"),
```

**Platform audit** — add to `backend/apps/organization/platform/urls.py`:
```python
path("audit/", AuditPlatformView.as_view(), name="platform-audit"),
```

**Governance audit** — add to `backend/backend_core/urls/governance.py`:
```python
path("api/v1/governance/audit/", GovernanceAuditListView.as_view(), name="governance-audit"),
```

### Step 5: Write tests

**New file:** `backend/apps/core/observability/audit/tests/test_views.py`

Test matrix:
- Business: member with permission → 200, member without → 403, non-member → 403
- Platform: platform member with permission → 200, without → 403
- Governance: Global Moderator with gov token → 200, without gov token → 403, regular user → 403
- Filters: action, outcome, since/until, actor_id, resource_type
- Pagination: page, page_size, cursor (governance)
- Empty results → 200 with empty list

**File:** `backend/apps/core/observability/audit/tests/test_selectors.py`

Tests for new selector methods: list_for_business, list_for_platform, list_all with filter combinations.

---

## Files Summary

### New files (3):

| File | Purpose |
|------|---------|
| `backend/apps/core/observability/audit/serializers.py` | AuditLogOutput serializer |
| `backend/apps/core/observability/audit/views.py` | 3 audit list views (business, platform, governance) |
| `backend/apps/core/observability/audit/tests/test_views.py` | View tests |

### Modified files (4):

| File | Changes |
|------|---------|
| `backend/apps/core/observability/audit/selectors.py` | Add list_for_business(), list_for_platform(), list_all(), _apply_common_filters() |
| `backend/apps/organization/business/urls.py` | Add `{slug}/audit/` path |
| `backend/apps/organization/platform/urls.py` | Add `audit/` path |
| `backend/backend_core/urls/governance.py` | Add `governance/audit/` path |

### Optionally modified (1):

| File | Changes |
|------|---------|
| `backend/apps/core/observability/audit/tests/test_selectors.py` | Add tests for new selector methods |

---

## Key Patterns to Reuse

| Pattern | Source | Lines |
|---------|--------|-------|
| AuditSelector.get_by_actor() | `audit/selectors.py` | 34-58 |
| AuditSelector.get_by_action() | `audit/selectors.py` | 77-101 |
| StandardPagination | `apps/core/pagination/page.py` | 33-59 |
| LargeResultsPagination | `apps/core/pagination/page.py` | 76-92 |
| GovernanceTokenRequired | `apps/core/permissions/governance.py` | 23-62 |
| BusinessPolicy._has_global_permission() | `business/policies.py` | 47-79 |
| PlatformPolicy._has_platform_permission() | `platform/policies.py` | 20-45 |
| BusinessAccountSelector.get_by_slug() | `business/selectors.py` | ~100 |
| GovernanceBusinessListView (pagination in view) | `business/governance_views.py` | reference |

---

## Verification

### Backend:
```bash
cd backend
black . && isort . && flake8 .
DJANGO_SETTINGS_MODULE=backend_core.settings.local python -m pytest apps/core/observability/audit/tests/ -v --tb=short
DJANGO_SETTINGS_MODULE=backend_core.settings.local python -m pytest --tb=short -q  # full suite
```

### Manual:
1. Create some audit logs by performing actions (login, create business, suspend)
2. `GET /api/v1/business/{slug}/audit/` → returns business-scoped logs
3. `GET /api/v1/platform/audit/` → returns platform-scoped logs
4. `GET /api/v1/governance/audit/` (with governance token) → returns all logs
5. Test filters: `?action=org.business.suspended&since=2026-04-01T00:00:00Z`
6. Test pagination: `?page=1&page_size=5`
