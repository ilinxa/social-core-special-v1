# Transaction System — Implementation Guide

**Version:** 2.0  
**Date:** February 12, 2026

---

## Purpose

This is the master guide for implementing the Transaction System — a unified engine for all "needs confirmation" flows (invitations, requests, approvals, ownership transfers). The implementation is split into 3 sequential phases, each with its own document.

---

## System Summary

The Transaction System centralizes membership invitations/requests, user connections, business verification, permission requests, and ownership transfers into a single state machine engine with pluggable outcome handlers.

**Core concepts:**
- `TransactionTypeConfig` — declarative config per transaction type (permissions, approver policy, payload schema, expiration)
- `Transaction` model — a state machine: `CREATED → PENDING → {ACCEPTED | DENIED | CANCELLED | DISMISSED | EXPIRED | INVALIDATED}`
- `OutcomeHandlerRegistry` — pluggable handlers executed when a transaction is accepted (e.g., create membership, transfer ownership)
- Dual authority validation — creator's permission re-checked at acceptance time

---

## Dependencies

```
HARD (must exist before Phase 1):
  apps.core          — UUIDModel, AuditModel, SoftDeleteManager, ActorContext, exceptions, AuditService
  apps.users         — User model
  apps.rbac          — RBACService (incl. transfer_ownership — see Pre-Phase), MembershipSelector, PermissionSelector, RoleSelector
  apps.organization  — Platform, Business account models, BusinessAccountService, ContextType, AccountType

PRE-PHASE REQUIRED (must be done before Phase 1):
  apps.rbac.services.RBACService.transfer_ownership() — currently a stub, must be implemented
  apps.notifications.types — 6 transaction notification types must be registered

SOFT (graceful if absent):
  apps.notifications — wrapped in try/except ImportError
  apps.formbuilder   — form response validation
```

---

## Phase Documents

### Pre-Phase: Dependency Updates (before creating the transaction app)

**What:** Register transaction notification types and implement `RBACService.transfer_ownership()` stub.

**Why:** The transaction system's notification helpers reference 6 notification types that don't exist yet. The ownership transfer outcome handler calls `transfer_ownership()` which is currently a `NotImplementedError` stub.

**Tasks:**
1. Add 6 notification types to `apps/notifications/types.py`: `transaction_invitation_received`, `transaction_accepted`, `transaction_denied`, `transaction_cancelled`, `transaction_expired`, `transaction_expiring_soon`
2. Implement `RBACService.transfer_ownership()` in `apps/rbac/services.py` (replace stub at line ~673)
3. Run `make test` — all 1822+ existing tests must pass

**Files modified:**
- `apps/notifications/types.py`
- `apps/rbac/services.py`

---

### Phase 1: Foundation (`transaction_phase1_foundation.md`)

**What:** App structure, constants, enums, type registry, models, managers, migrations, new audit actions.

**Depends on:** `apps.core`, `apps.organization` (for `ContextType`)

**Deliverable:** `python manage.py makemigrations transaction` succeeds. Models exist in DB. No business logic yet.

**Files created:**
```
apps/transaction/__init__.py
apps/transaction/apps.py
apps/transaction/constants.py
apps/transaction/types.py
apps/transaction/models.py
apps/transaction/managers.py
apps/transaction/migrations/0001_initial.py
```

**Also modifies:**
- `apps/core/observability/audit/models.py` — add 7 transaction audit actions
- Core migration for new audit actions

---

### Phase 2: Business Logic (`transaction_phase2_business_logic.md`)

**What:** Selectors, policies, services (all state transitions), outcome handlers, creator authority re-validation, notification helpers. New RBAC permissions.

**Depends on:** Phase 1 complete. `apps.rbac` services/selectors.

**Deliverable:** All service methods callable. `TransactionService.create_invitation()`, `.accept()`, `.deny()`, `.cancel()`, `.expire()`, `.invalidate()` all work. Unit tests pass.

**Files created:**
```
apps/transaction/selectors.py
apps/transaction/policies.py
apps/transaction/services.py
apps/transaction/outcome_handlers.py
apps/transaction/signals.py
apps/transaction/tests/conftest.py
apps/transaction/tests/factories.py
apps/transaction/tests/test_services.py
apps/transaction/tests/test_policies.py
apps/transaction/tests/test_outcome_handlers.py
```

**Also modifies:**
- `apps/rbac/permissions/registry.py` — add `can_view_transactions`, `can_view_all_transactions`
- RBAC migration for new permissions + backfill

---

### Phase 3: Interface Layer (`transaction_phase3_interface.md`)

**What:** API views, serializers, URLs, `TransactionContextMixin`, Celery tasks, Celery Beat config, rate limiting.

**Depends on:** Phase 2 complete.

**Deliverable:** REST endpoints callable. Background expiration/cleanup tasks scheduled. Full integration tests pass.

**Files created:**
```
apps/transaction/api/__init__.py
apps/transaction/api/serializers.py
apps/transaction/api/views.py
apps/transaction/api/urls.py
apps/transaction/tasks.py
apps/transaction/rate_limits.py
apps/transaction/tests/test_views.py
apps/transaction/tests/test_tasks.py
```

**Also modifies:**
- `backend_core/urls.py` — add transaction URL include
- `backend_core/celery.py` — add Celery Beat schedules

---

## Implementation Order

```
0. Pre-Phase → update notification types + implement transfer_ownership → make test → all pass
1. Read Phase 1 → implement → makemigrations → migrate → verify models in DB
2. Read Phase 2 → implement → run pytest apps/transaction/tests/ → all pass
3. Read Phase 3 → implement → run full test suite → endpoints respond
```

Each phase is a clean stopping point. You can ship Phase 1+2 without the API layer if needed.

> **Important:** See the review corrections document for 17 issues found during plan review.
> Critical fixes have been applied directly to the phase documents. The corrections plan
> is at `.claude/plans/declarative-doodling-wadler.md` for reference.

---

## Key Design Decisions (reference)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State machine | No `SENT` state | Was dead — `CREATED → SENT → PENDING` happened atomically |
| Cancel vs Revoke | Single `cancel` from `PENDING` | `revoke` was redundant |
| Permission checks | `ActorContext.has_permission()` | `permissions_snapshot` is `List[Tuple[str, str]]`, not flat strings |
| AuditService calls | `actor=_resolve_actor(ctx)` | `AuditService.log` expects `actor=User`, not `actor_id=UUID` |
| Authority re-validation | `PermissionSelector.get_permissions_for_membership()` | No `membership.get_permissions()` method exists |
| Default role lookup | `RoleSelector.get_base_member_role()` | No `get_default_for_account()` method exists |
| Ownership check | `config.owner_only` field | Replaces `"ownership_transfer" in config.id` string-match |
| Approval permission | `config.approval_permission` field | Replaces hardcoded permission map in policy |
| Notifications | `_notify_safe()` with `try/except ImportError` | Notification system may not exist yet |
| View context resolution | `TransactionContextMixin` | `TARGET_ACCEPTANCE` needs user context; `ACCOUNT_AUTHORITY`/`PLATFORM_AUTHORITY` need account-bound context |

---

## State Machine Reference

```
    ┌──────────┐
    │ CREATED  │
    └────┬─────┘
         │ (immediate, same atomic transaction)
         ▼
    ┌──────────┐
    │ PENDING  ├──────────────────────────────┐
    └──┬───┬───┘                              │
       │   │                                   │
  ┌────▼┐ ┌▼──────┐  ┌─────────┐  ┌──────────▼───┐
  │ACC- │ │DENIED │  │DISMISSED│  │  CANCELLED   │
  │EPTED│ │       │  │(no cool-│  │  (initiator) │
  └──┬──┘ └───────┘  │ down)   │  └──────────────┘
     │                └─────────┘
  outcome                         ┌─────────┐  ┌─────────────┐
  handler()                       │ EXPIRED │  │ INVALIDATED │
                                  │ (cron)  │  │ (authority  │
                                  └─────────┘  │  lost)      │
                                               └─────────────┘
```

All bottom-row states are **TERMINAL** — no further transitions.
