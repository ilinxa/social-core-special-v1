# Multi-Tenant Platform — Implementation Guide

**Version:** 1.0 | **Date:** February 8, 2026

---

## System Overview

| # | System | Version | Plan Location | Purpose |
|---|--------|---------|---------------|---------|
| 1 | Organization | v1.2 | `system_1_plans/organization_system_implementation_plan.md` | Accounts (Platform singleton, Business), verification |
| 2 | Transaction | v1.1 | `system_2_plans/transaction_system_implementation_plan.md` | Async workflows (invitations, transfers, verifications) |
| 3 | RBAC | v1.2 | `system_3_plans/rbac_system_implementation_plan.md` | Roles, permissions, memberships |
| 4 | Form Builder | v1.0 | `system_4_plans/form_builder_system_implementation_plan.md` | Dynamic forms, responses, indexing |

**Shared Reference:** `predocs/system_1/Shared_System_Context.md` (v1.2)

---

## Implementation Order

```
┌─────────────────┐
│ 1. ORGANIZATION │  ← Foundation: accounts, enums
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    2. RBAC      │  ← Roles, permissions, ActorContext
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. TRANSACTION  │  ← Async workflows, outcome handlers
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. FORM BUILDER │  ← Dynamic forms, optional Transaction binding
└─────────────────┘
```

### Why This Order?

1. **Organization** — No dependencies. Creates `PlatformAccount`, `BusinessAccount`. Defines shared enums.
2. **RBAC** — Needs accounts. Creates `Role`, `Permission`, `Membership`. Provides `ActorContext`.
3. **Transaction** — Needs RBAC (permissions) + Organization (accounts). Handles invitations, transfers.
4. **Form Builder** — Needs RBAC + Organization. Optional: binds to Transaction for workflows.

---

## Critical Rules (All Systems)

### ActorContext
```python
# ✅ CORRECT - Always use RBACService
from apps.rbac.services import RBACService
actor_context = RBACService.build_actor_context(membership=membership, request=request)

# ❌ WRONG - Never construct directly
actor_context = ActorContext(...)  # NO!
```

### Base Models
```python
from apps.core.models import UUIDModel, AuditModel

class MyModel(UUIDModel, AuditModel):  # UUID pk + created_at/updated_at + created_by/updated_by
    pass
```

### Observability
```python
from apps.core.observability import get_logger, AuditService, AuditLog

logger = get_logger(__name__)
AuditService.log(action=AuditLog.Action.SOME_ACTION, actor_context=actor_context, ...)
```

### Service Pattern
- All writes go through services (keyword-only args)
- All reads go through selectors
- Views are thin HTTP orchestration

---

## Quick Reference per System

### 1. Organization
| Item | Detail |
|------|--------|
| Models | `PlatformAccount` (singleton), `BusinessAccount`, `BusinessVerification` |
| Singleton | Constraint on `singleton_key=1` — DB enforced |
| Enums | `AccountType`, `ContextType`, `PermissionScope`, `VerificationStatus` |
| RBAC Stub | Call `RBACService.initialize_business_account()` on create |

### 2. RBAC
| Item | Detail |
|------|--------|
| Models | `Role`, `Permission`, `Membership`, `RolePermission` |
| is_owner | Flag on `Membership`, NOT role name |
| Predefined Roles | Owner (0), Admin (1), Manager (3), Member (5), Viewer (7), Base (10) |
| Cache | 5-min TTL, invalidate on role/permission change |
| ActorContext | Pure data in `core/types.py`, factory in `RBACService` |

### 3. Transaction
| Item | Detail |
|------|--------|
| Models | `TransactionType`, `Transaction`, `TransactionHistory` |
| Lifecycle | PENDING → ACCEPTED/REJECTED/CANCELLED/EXPIRED |
| Outcome | `TransactionOutcomeService.process()` executes side effects |
| Token | 64-char URL-safe, hashed in DB |
| Expiry | Celery task for auto-expiration |

### 4. Form Builder
| Item | Detail |
|------|--------|
| Models | `FormTemplate`, `FormField`, `FormResponse`, 6 Index Tables |
| Max Indexed | 5 fields per form (service-enforced) |
| Versioning | Edit active → new version, `is_current=True` |
| Library | Fork with `forked_from` reference |
| Storage | JSON + selective typed indexes |

---

## Files Created per System

| System | New App | Core Modifications |
|--------|---------|-------------------|
| Organization | `apps/organization/` | `core/constants.py` (enums), audit actions |
| RBAC | `apps/rbac/` | `core/types.py` (ActorContext), audit actions |
| Transaction | `apps/transactions/` | audit actions |
| Form Builder | `apps/forms/` | `core/constants.py` (enums), audit actions |

---

## Implementation Checklist

For each system:
- [ ] Read the full plan
- [ ] Create app directory structure
- [ ] Add enums to `core/constants.py` if needed
- [ ] Add audit actions to `core/observability/audit/models.py`
- [ ] Implement models → managers → selectors → services → policies → serializers → views → urls
- [ ] Add to `INSTALLED_APPS` in `backend_core/settings/base.py`
- [ ] Add URLs to `backend_core/urls.py`
- [ ] Create migrations (`make makemigrations`)
- [ ] Write tests (80%+ coverage)
- [ ] Run `make check`

---

## Ownership Transfer (3-Stage Audit)

```
Organization                    Transaction                     RBAC
     │                              │                            │
     └─ OWNERSHIP_TRANSFER_INITIATED ─► Transaction created      │
                                    │                            │
                                    └─ Transaction accepted ───► OWNERSHIP_TRANSFERRED
                                                                 │
                                                                 └─ OWNER_MEMBERSHIP_CREATED
```

---

## Permission Scopes

| Scope | Meaning |
|-------|---------|
| `business` | Within single business |
| `platform_only` | Platform-level only |
| `global_only` | Global (super admin) |

---

*End of Guide*
