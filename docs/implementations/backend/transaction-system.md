# Transaction System — Implementation Reference

**Version:** v2
**Last Updated:** 2026-02-24
**Status:** Implemented

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  API Layer (api/views.py)                                        │
│  12 views: List, Detail, Create (Inv/Req), Accept, Deny,        │
│            Cancel, Dismiss, FormSchema, RequestInfo, Resubmit,   │
│            FormResponse                                          │
│  TransactionContextMixin → resolves ActorContext per policy       │
├──────────────────────────────────────────────────────────────────┤
│  Serializers (api/serializers.py)                                │
│  5 input + 3 output serializers                                  │
├──────────────────────────────────────────────────────────────────┤
│  Service Layer (services.py)                                     │
│  TransactionService: create, accept, deny, dismiss, cancel,      │
│                      expire, invalidate, request_info,           │
│                      resubmit_after_info_request                 │
│  + private: _transition, _validate_payload, _execute_outcome,    │
│             _validate_creator_authority, _notify_safe,            │
│             _validate_form_requirement, _link_form_response      │
├─────────────────────┬────────────────────────────────────────────┤
│  Policies            │  Outcome Handlers                          │
│  (policies.py)       │  (outcome_handlers.py)                     │
│  can_create,         │  Registry + 6 handlers                     │
│  can_accept/deny,    │  MembershipOutcome, Verification,          │
│  can_view,           │  Ownership, Connection, Follow,            │
│  is_initiator        │  Permission                                │
├─────────────────────┴────────────────────────────────────────────┤
│  Selectors (selectors.py)           │  Rate Limits               │
│  TransactionSelector (11 methods)    │  (rate_limits.py)          │
│  TransactionLogSelector (1 method)   │  check_rate_limit()        │
├──────────────────────────────────────┤                            │
│  Managers (managers.py)              │                            │
│  TransactionQuerySet (8 methods)     │                            │
│  TransactionManager (create + proxy) │                            │
├──────────────────────────────────────┴────────────────────────────┤
│  Data Layer (models.py)                                          │
│  Transaction (UUID, soft-delete, 6 indexes, 1 check constraint)  │
│  TransactionLog (immutable, UUID, cascade FK)                    │
├──────────────────────────────────────────────────────────────────┤
│  Constants (constants.py)  │  Types (types.py)                   │
│  4 enums, state machine    │  10 TransactionTypeConfig instances  │
│  + INFO_REQUESTED status   │  + slug-based form requirements      │
├──────────────────────────────────────────────────────────────────┤
│  Tasks (tasks.py) — 4 Celery tasks                               │
│  expire, retry_outcome, cleanup_logs, expiration_reminder        │
└──────────────────────────────────────────────────────────────────┘

External dependencies:
  → apps.rbac (RBACService, MembershipSelector, RoleSelector, permissions)
  → apps.core (ActorContext, AuditService, exceptions, pagination)
  → apps.notifications (NotificationService, 8 notification types)
  → apps.forms (FormResponseService, FormResponseSelector, FormTemplateSelector)
  → apps.organization.business (BusinessAccountService, BusinessAccountSelector)
  → apps.users (User model, UserFactory)
```

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Unified state machine | Single `Transaction` model for all 10 types | Avoids 10 separate models/tables; consistent lifecycle, single audit trail |
| Pluggable outcome handlers | `OutcomeHandlerRegistry` with per-type handlers | Decouples state transitions from side effects; new types only need a handler function |
| Dual authority validation | Creator's permissions re-checked at acceptance | Prevents stale invitations from being accepted after initiator lost permissions |
| Immutable audit log | `TransactionLog` raises `ValueError` on update/delete | Ensures tamper-proof event history for compliance |
| Party abstraction | `PartyType` enum (USER, ACCOUNT, MEMBERSHIP_ACTOR, SYSTEM) | Supports user-to-user, user-to-account, and account-to-user flows |
| Config-driven types | `TransactionTypeConfig` dataclass with 18 fields | All business rules (permissions, payload schema, cooldowns, expiration) declared in one place |
| Soft-delete via base model | Inherits `AuditModel` with `is_deleted` | Consistent with other apps; `objects` manager auto-filters |
| AUTO_APPROVAL policy | Auto-transitions to ACCEPTED in `create_request` | Enables follow-like flows without manual approval step |
| Slug-based form requirements | `required_form_template_slug` on TransactionTypeConfig | Config declares which system form template is required by slug; validated at creation time, bidirectional linking established automatically |

---

## 3. Data Layer

### 3.1 Transaction

Location: `apps/transaction/models.py`

Inherits: `UUIDModel` (UUID pk) + `AuditModel` (created_at, updated_at, created_by, updated_by, is_deleted, deleted_at, deleted_by)

| Field | Type | Notes |
|-------|------|-------|
| `transaction_type` | CharField(100) | Indexed, maps to `TRANSACTION_TYPES` key |
| `mode` | CharField(choices=TransactionMode) | "invitation" or "request" |
| `initiator_type` | CharField(choices=PartyType) | USER, ACCOUNT, MEMBERSHIP_ACTOR, or SYSTEM |
| `initiator_id` | UUIDField | User UUID or Membership UUID |
| `initiator_context` | JSONField | `ActorContext.to_dict()` snapshot at creation |
| `target_type` | CharField(choices=PartyType) | USER or ACCOUNT |
| `target_id` | UUIDField | User UUID or Account UUID |
| `context_type` | CharField(choices=ContextType) | PLATFORM, BUSINESS, or USER; indexed |
| `context_id` | UUIDField(null, blank) | Account UUID; NULL for user context; indexed |
| `status` | CharField(choices=TransactionStatus) | Default "created"; indexed |
| `payload` | JSONField(default=dict) | Type-specific data (role_id, message, etc.) |
| `form_response_id` | UUIDField(null, blank, db_index=True) | Link to form submission |
| `info_requested_at` | DateTimeField(null, blank) | When info was requested |
| `info_requested_by` | FK→User(SET_NULL, null) | Who requested info; related_name="info_requested_transactions" |
| `info_requested_message` | TextField(blank) | Message to initiator explaining what's needed |
| `info_requested_fields` | JSONField(default=list) | Specific field keys requested for update |
| `expires_at` | DateTimeField(null, blank) | Auto-set from `config.expiration_days`; indexed |
| `resolved_at` | DateTimeField(null, blank) | Set on terminal transition |
| `resolved_by` | FK→User(SET_NULL, null) | User who resolved; related_name="resolved_transactions" |
| `resolution_reason` | TextField(blank) | Deny/invalidate reason |
| `outcome_executed` | BooleanField(default=False) | Whether outcome handler ran |
| `outcome_executed_at` | DateTimeField(null, blank) | When outcome executed |
| `outcome_error` | TextField(blank) | Error from failed outcome |

**Indexes:**
- `(transaction_type, status)`
- `(context_type, context_id, status)`
- `(initiator_type, initiator_id)`
- `(target_type, target_id)`
- `(expires_at,)`
- `(status, outcome_executed)`

**Constraints:**
- `txn_context_id_required_for_account_contexts`: `context_type="user" OR context_id IS NOT NULL`

**Properties:**
- `is_terminal` → `bool`: status in `TERMINAL_STATES`
- `is_expired` → `bool`: `expires_at is not None and now() > expires_at`
- `can_transition_to(new_status)` → `bool`: checks `VALID_TRANSITIONS`

**Manager:** `objects = TransactionManager()` (soft-delete aware), `all_objects = models.Manager()`

### 3.2 TransactionLog

Location: `apps/transaction/models.py`

Self-contained model (no base class inheritance). UUID primary key.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk, default=uuid4) | Auto-generated |
| `transaction` | FK→Transaction(CASCADE) | related_name="logs" |
| `event_type` | CharField(50) | "created", "state_changed", etc.; indexed |
| `timestamp` | DateTimeField(default=now) | Indexed |
| `actor_context` | JSONField(default=dict) | ActorContext snapshot |
| `previous_status` | CharField(choices, blank) | Before transition |
| `new_status` | CharField(choices) | After transition |
| `metadata` | JSONField(default=dict) | Extra data per event |

**Immutability enforced:**
- `save()` raises `ValueError("TransactionLog entries cannot be modified")` if `self.pk` exists in DB
- `delete()` raises `ValueError("TransactionLog entries cannot be deleted")`

**Ordering:** `["-timestamp"]`
**Index:** `(transaction, timestamp)`

### Migrations

- `0001_initial` — Creates Transaction and TransactionLog tables with all indexes and constraints
- `0002_add_info_requested_fields` — Adds info_requested_at, info_requested_by, info_requested_message, info_requested_fields to Transaction; adds db_index to form_response_id

---

## 4. Service Layer

### 4.1 TransactionService

Location: `apps/transaction/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_invitation` | transaction_type, initiator_context, target_user_id, payload?, form_response_id?, request? | Transaction | `@transaction.atomic`. Validates mode=INVITATION, enabled, permissions, no duplicates, payload schema. Creates CREATED→PENDING, audits, notifies on_commit |
| `create_request` | transaction_type, user_id, target_account_type?, target_account_id?, target_user_id?, payload?, form_response_id?, request? | Transaction | `@transaction.atomic`. Validates mode=REQUEST, enabled, no duplicates, cooldown. For AUTO_APPROVAL: auto-accepts and executes outcome |
| `accept` | transaction_id, actor_context, request? | Transaction | `@transaction.atomic`. Policy check, re-validates creator authority (invitations), transitions to ACCEPTED, executes outcome |
| `deny` | transaction_id, actor_context, reason?, request? | Transaction | `@transaction.atomic`. Policy check, transitions to DENIED with reason |
| `dismiss` | transaction_id, actor_context, request? | Transaction | `@transaction.atomic`. Validates mode=REQUEST, transitions to DISMISSED |
| `cancel` | transaction_id, actor_context, request? | Transaction | `@transaction.atomic`. Validates is_initiator, transitions to CANCELLED |
| `expire` | transaction_id | Transaction | `@transaction.atomic`. Returns if terminal, transitions to EXPIRED |
| `invalidate` | transaction_id, reason | Transaction | `@transaction.atomic`. Returns if terminal, transitions to INVALIDATED |
| `request_info` | transaction_id, message, requested_fields?, actor_context, request? | Transaction | `@transaction.atomic`. Validates PENDING + has form + can_accept policy, sets info fields, transitions PENDING→INFO_REQUESTED, marks form response, audits `TRANSACTION_INFO_REQUESTED` |
| `resubmit_after_info_request` | transaction_id, actor_context, request? | Transaction | `@transaction.atomic`. Validates INFO_REQUESTED + is_initiator, transitions INFO_REQUESTED→PENDING, audits `TRANSACTION_RESUBMITTED` |

**Private helpers:**

| Method | Purpose |
|--------|---------|
| `_transition` | State machine: validates transition, updates status/resolved_at/resolved_by, logs event |
| `_log_event` | Creates TransactionLog entry |
| `_validate_payload` | Validates payload against `config.payload_schema` (required, type, max_length) |
| `_validate_creator_authority` | Re-checks initiator's membership and permissions at acceptance time; calls `invalidate()` if lost |
| `_execute_outcome` | Calls `OutcomeHandlerRegistry.execute()`; marks `outcome_executed=True` on success |
| `_notify_safe` | Gracefully degrading notification dispatch (catches ImportError and exceptions) |
| `_validate_form_requirement` | Validates form_response_id against config's required_form_template_slug; checks template slug matches |
| `_link_form_response` | Calls FormResponseService.link_to_transaction() for bidirectional linking |
| `_notify_invitation_created` | Sends `transaction_invitation_received` to target |
| `_notify_accepted` | Sends `transaction_accepted` to initiator |
| `_notify_denied` | Sends `transaction_denied` to initiator |
| `_notify_cancelled` | Sends `transaction_cancelled` to target |
| `_notify_expired` | Sends `transaction_expired` to initiator |
| `_notify_info_requested` | Sends `transaction_info_requested` to initiator |
| `_notify_resubmitted` | Stub — notify approvers (future enhancement) |

### 4.2 Selectors

Location: `apps/transaction/selectors.py`

**TransactionSelector:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_by_id` | transaction_id | Transaction | Raises `NotFound` |
| `get_by_id_or_none` | transaction_id | Transaction? | Returns None |
| `get_by_id_with_logs` | transaction_id | Transaction | Prefetches logs; raises `NotFound` |
| `exists_active` | transaction_type, initiator_id, target_id | bool | Checks for non-terminal duplicate |
| `list_for_user_as_initiator` | user_id, include_terminal? | QuerySet | Filters by initiator_type=USER, ordered by -created_at |
| `list_for_user_as_target` | user_id, include_terminal? | QuerySet | Filters by target_type=USER, ordered by -created_at |
| `list_pending_for_context` | context_type, context_id, transaction_type? | QuerySet | Pending transactions for an account |
| `list_expired_needing_update` | — | QuerySet | Uses manager's `expired_needing_update()` |
| `get_resubmission_cooldown` | transaction_type, initiator_id, target_id | datetime? | Returns cooldown end if within window |
| `get_by_form_response_id` | form_response_id | Transaction? | Returns None if not found |
| `get_form_template_for_type` | transaction_type | FormTemplate? | Resolves slug from config, looks up system form via FormTemplateSelector |

**TransactionLogSelector:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `list_for_transaction` | transaction_id | QuerySet | Ordered by -timestamp |

### 4.3 Policies

Location: `apps/transaction/policies.py`

| Method | Args | Behavior |
|--------|------|----------|
| `can_create_invitation` | actor_context, config | Checks required_permissions and owner_only flag |
| `can_accept` | transaction, actor_context, config | Routes by ApproverPolicy: TARGET_ACCEPTANCE checks user==target, ACCOUNT_AUTHORITY checks membership+permission, PLATFORM_AUTHORITY checks platform membership+permission, AUTO_APPROVAL raises ValidationError |
| `can_deny` | transaction, actor_context, config | Delegates to `can_accept` (same checks) |
| `is_initiator` | transaction, actor_context | Compares user_id from `initiator_context` against `actor_context.user_id` |
| `can_view` | transaction, actor_context | Initiator/target always; account members with `can_view_transactions`; platform with `can_view_all_transactions` |

### 4.4 Outcome Handlers

Location: `apps/transaction/outcome_handlers.py`

**Registry:** `OutcomeHandlerRegistry` — dict-based `{type_id: callable}`, called via `execute(transaction, actor_context)`.

| Handler Class | Method | Called By Types | Effect |
|--------------|--------|-----------------|--------|
| MembershipOutcomeHandler | `handle_invitation_accepted` | platform/business_membership_invitation | `RBACService.create_membership(user=, created_by=)` |
| MembershipOutcomeHandler | `handle_request_approved` | platform/business_membership_request | `RBACService.create_membership` with base role fallback |
| VerificationOutcomeHandler | `handle_accepted` | business_verification_request | `BusinessAccountService.update_verification_status` |
| OwnershipOutcomeHandler | `handle_accepted` | platform/business_ownership_transfer | `RBACService.transfer_ownership(new_owner=, transferred_by=)` |
| ConnectionOutcomeHandler | `handle_accepted` | user_connection_request | Stub — logs only |
| FollowOutcomeHandler | `handle_accepted` | business_follow_request | Stub — logs only |
| PermissionOutcomeHandler | `handle_business_creation_approved` | business_creation_permission_request | Stub — logs only |

`register_all_handlers()` maps all 10 types to their handlers. Called at app startup.

---

## 5. API Layer

### 5.1 Endpoints

Base path: `/api/v1/transactions/`

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/` | GET | TransactionListView | IsAuthenticated | List user's transactions (filter: `?role=initiator\|target\|all`) |
| `/invitation/` | POST | CreateInvitationView | IsAuthenticated + RBAC | Create invitation (requires membership in context) |
| `/request/` | POST | CreateRequestView | IsAuthenticated | Create request |
| `/<uuid>/` | GET | TransactionDetailView | IsAuthenticated + Policy | View transaction with logs |
| `/<uuid>/accept/` | POST | AcceptTransactionView | IsAuthenticated + Policy | Accept transaction |
| `/<uuid>/deny/` | POST | DenyTransactionView | IsAuthenticated + Policy | Deny transaction (optional reason) |
| `/<uuid>/cancel/` | POST | CancelTransactionView | IsAuthenticated + Policy | Cancel (initiator only) |
| `/<uuid>/dismiss/` | POST | DismissTransactionView | IsAuthenticated + Policy | Dismiss request (authority only) |
| `/types/<type>/form/` | GET | TransactionFormSchemaView | IsAuthenticated | Get form template for transaction type |
| `/<uuid>/request-info/` | POST | TransactionRequestInfoView | IsAuthenticated + Policy | Request additional info from initiator |
| `/<uuid>/resubmit/` | POST | TransactionResubmitView | IsAuthenticated | Resubmit after updating form response |
| `/<uuid>/form-response/` | GET/PATCH | TransactionFormResponseView | IsAuthenticated + Policy | View/update linked form response |

`TransactionContextMixin` resolves the correct `ActorContext` based on the transaction's `ApproverPolicy`: user context for TARGET_ACCEPTANCE, membership context for ACCOUNT/PLATFORM_AUTHORITY.

### 5.2 Serializers

Location: `apps/transaction/api/serializers.py`

| Serializer | Type | Key Fields | Notes |
|------------|------|------------|-------|
| CreateInvitationInputSerializer | Input | transaction_type, target_user_id, context_type, context_id, payload?, form_response_id? | Requires context membership |
| CreateRequestInputSerializer | Input | transaction_type, target_account_id?, target_account_type?, target_user_id?, payload?, form_response_id? | Validates at least one target provided |
| DenyTransactionInputSerializer | Input | reason? | Optional, max 1000 chars |
| RequestInfoInputSerializer | Input | message, requested_fields? | Message required, max 2000 chars |
| FormResponseUpdateInputSerializer | Input | data (JSONField) | Update form response data |
| TransactionLogOutputSerializer | Output | id, event_type, timestamp, previous_status, new_status, metadata | Nested in TransactionOutputSerializer |
| TransactionOutputSerializer | Output | All fields + nested logs | Full detail view + form_response_id, info_requested_at/message/fields, inline form_response SerializerMethodField |
| TransactionListSerializer | Output | id, transaction_type, mode, status, expires_at, created_at | Compact list view |

---

## 6. Types & Constants

### Enums

| Enum | Values |
|------|--------|
| `TransactionMode` | INVITATION, REQUEST |
| `TransactionStatus` | CREATED, PENDING, ACCEPTED, DENIED, CANCELLED, EXPIRED, DISMISSED, INVALIDATED, INFO_REQUESTED |
| `PartyType` | USER, ACCOUNT, MEMBERSHIP_ACTOR, SYSTEM |
| `ApproverPolicy` | TARGET_ACCEPTANCE, ACCOUNT_AUTHORITY, PLATFORM_AUTHORITY, AUTO_APPROVAL |

### State Machine

```
CREATED → PENDING → ACCEPTED
                   → DENIED
                   → CANCELLED
                   → DISMISSED
                   → EXPIRED
                   → INVALIDATED
                   → INFO_REQUESTED → PENDING (resubmit)
                                     → CANCELLED
                                     → EXPIRED
                                     → INVALIDATED

CREATED → EXPIRED (direct, if expired before pending)
CREATED → INVALIDATED (direct, if creator lost authority)
```

Terminal states: `{ACCEPTED, DENIED, CANCELLED, EXPIRED, DISMISSED, INVALIDATED}`

### Transaction Types (10)

| Type ID | Mode | Context | Approver Policy | Outcome |
|---------|------|---------|-----------------|---------|
| platform_membership_invitation | INVITATION | PLATFORM | TARGET_ACCEPTANCE | Create membership |
| platform_membership_request | REQUEST | PLATFORM | PLATFORM_AUTHORITY | Create membership |
| platform_ownership_transfer | INVITATION | PLATFORM | TARGET_ACCEPTANCE | Transfer ownership |
| business_membership_invitation | INVITATION | BUSINESS | TARGET_ACCEPTANCE | Create membership |
| business_membership_request | REQUEST | BUSINESS | ACCOUNT_AUTHORITY | Create membership |
| business_verification_request | REQUEST | PLATFORM | PLATFORM_AUTHORITY | Update verification status; required_form=system-business-verification |
| business_follow_request | REQUEST | BUSINESS | AUTO_APPROVAL | Create follow (stub) |
| business_ownership_transfer | INVITATION | BUSINESS | TARGET_ACCEPTANCE | Transfer ownership |
| business_creation_permission_request | REQUEST | PLATFORM | PLATFORM_AUTHORITY | Grant permission (stub) |
| user_connection_request | REQUEST | USER | TARGET_ACCEPTANCE | Create connection (stub) |

---

## 7. Key Flows

### Flow 1: Create Invitation (e.g., business_membership_invitation)

1. Client POSTs to `/api/v1/transactions/invitation/` with `transaction_type`, `target_user_id`, `context_type`, `context_id`, `payload`
2. View resolves membership and builds `ActorContext` via `RBACService.build_actor_context()`
3. `TransactionService.create_invitation()`:
   - Validates config mode=INVITATION, enabled
   - `TransactionPolicy.can_create_invitation()` checks RBAC permissions
   - Checks no active duplicate exists
   - Validates payload against `config.payload_schema`
   - Creates Transaction (status=CREATED)
   - Logs "created" event → transitions to PENDING
   - Audits `TRANSACTION_CREATED`
   - Schedules notification on_commit (`transaction_invitation_received` to target)
4. Returns 201 with serialized transaction

### Flow 2: Accept Invitation (TARGET_ACCEPTANCE)

1. Target user POSTs to `/api/v1/transactions/<uuid>/accept/`
2. `TransactionContextMixin` detects TARGET_ACCEPTANCE → returns user context
3. `TransactionService.accept()`:
   - `TransactionPolicy.can_accept()` verifies `actor_context.user_id == transaction.target_id`
   - `_validate_creator_authority()` re-checks initiator's membership and permissions
     - If lost: calls `invalidate()` and raises `ValidationError`
   - Transitions PENDING → ACCEPTED with `resolved_by`
   - Audits `TRANSACTION_ACCEPTED`
   - `_execute_outcome()` → calls registered handler (e.g., `MembershipOutcomeHandler.handle_invitation_accepted`)
     - Handler calls `RBACService.create_membership(user=target, created_by=initiator)`
   - Schedules notification on_commit (`transaction_accepted` to initiator)
4. Returns 200 with updated transaction

### Flow 3: Auto-Approval (e.g., business_follow_request)

1. User POSTs to `/api/v1/transactions/request/` with `transaction_type=business_follow_request`
2. `TransactionService.create_request()`:
   - Creates Transaction (status=CREATED) → transitions to PENDING
   - Detects `config.approver_policy == AUTO_APPROVAL`
   - Auto-transitions PENDING → ACCEPTED
   - Executes outcome handler immediately (FollowOutcomeHandler)
   - Returns transaction already in ACCEPTED state
3. Returns 201 with status="accepted"

### Flow 4: Cancel (Initiator)

1. Initiator POSTs to `/api/v1/transactions/<uuid>/cancel/`
2. `TransactionService.cancel()`:
   - `TransactionPolicy.is_initiator()` — compares user_id from `initiator_context` dict
   - Validates status=PENDING
   - Transitions to CANCELLED
   - Audits `TRANSACTION_CANCELLED`
   - Notifies target on_commit
3. Returns 200 with status="cancelled"

### Flow 5: Creator Authority Invalidation

1. User A invites User B to business (invitation created, PENDING)
2. Admin removes User A from business (membership deactivated)
3. User B accepts invitation
4. `_validate_creator_authority()`:
   - Loads `initiator_context` from transaction
   - Looks up membership by `membership_id` — found but `is_active=False`
   - Calls `TransactionService.invalidate()` with reason
   - Raises `ValidationError("Creator's authority has been revoked")`
5. User B sees error; invitation is now INVALIDATED

### Flow 6: Hourly Expiration Task

1. `expire_transactions_task()` runs via Celery Beat
2. Queries `TransactionSelector.list_expired_needing_update()`
3. For each: calls `TransactionService.expire(transaction_id=txn.id)`
   - Transitions to EXPIRED
   - Schedules `transaction_expired` notification
4. Logs completion count

### Flow 7: Request Info (PENDING → INFO_REQUESTED)

1. Reviewer POSTs to `/<uuid>/request-info/` with `message` and optional `requested_fields`
2. `TransactionContextMixin` resolves ActorContext (same as accept/deny)
3. `TransactionService.request_info()`:
   - Validates status=PENDING and form_response_id exists
   - `TransactionPolicy.can_accept()` checks authority
   - Validates requested_fields exist in form template
   - Sets info_requested_at/by/message/fields on transaction
   - Transitions PENDING → INFO_REQUESTED
   - Calls `FormResponseService.mark_info_requested()` on linked response
   - Audits `TRANSACTION_INFO_REQUESTED`
   - Notifies initiator on_commit
4. Returns 200 with updated transaction

### Flow 8: Resubmit After Info Request (INFO_REQUESTED → PENDING)

1. Initiator updates form data via PATCH `/<uuid>/form-response/`
   - Calls `FormResponseService.update_after_info_request()`
   - Validates transaction is INFO_REQUESTED, validates submitter
   - Saves revision history, increments revision, re-extracts indexes
2. Initiator POSTs to `/<uuid>/resubmit/`
3. `TransactionService.resubmit_after_info_request()`:
   - Validates status=INFO_REQUESTED
   - `TransactionPolicy.is_initiator()` checks ownership
   - Transitions INFO_REQUESTED → PENDING
   - Audits `TRANSACTION_RESUBMITTED`
4. Returns 200 with status="pending" (ready for re-review)

---

## 8. Permissions & Authorization

### RBAC Permissions (seeded)

| Permission | Category | Scope | Used By |
|------------|----------|-------|---------|
| `can_view_transactions` | transaction | business, platform_only | `TransactionPolicy.can_view()` |
| `can_view_all_transactions` | transaction | global_only, platform_and_global | `TransactionPolicy.can_view()` |
| `can_invite_member` | membership | (existing) | `TransactionPolicy.can_create_invitation()` |
| `can_approve_membership_request` | membership | (existing) | `TransactionPolicy.can_accept()` |
| `can_approve_verification_request` | verification | (existing) | `TransactionPolicy.can_accept()` |
| `can_approve_business_creation` | business | (existing) | `TransactionPolicy.can_accept()` |

### Audit Actions

| Action | Constant | Triggered By |
|--------|----------|--------------|
| Transaction Created | `txn.created` | `create_invitation`, `create_request` |
| Transaction Accepted | `txn.accepted` | `accept` |
| Transaction Denied | `txn.denied` | `deny` |
| Transaction Dismissed | `txn.dismissed` | `dismiss` |
| Transaction Cancelled | `txn.cancelled` | `cancel` |
| Transaction Expired | `txn.expired` | `expire` |
| Transaction Invalidated | `txn.invalidated` | `invalidate` |
| Transaction Info Requested | `txn.info_requested` | `request_info` |
| Transaction Resubmitted | `txn.resubmitted` | `resubmit_after_info_request` |

### Notification Types (8)

| Type | Category | Channels | Triggered By |
|------|----------|----------|--------------|
| `transaction_invitation_received` | TRANSACTIONAL | EMAIL, PUSH | `create_invitation` on_commit |
| `transaction_accepted` | TRANSACTIONAL | EMAIL, PUSH | `accept` on_commit |
| `transaction_denied` | TRANSACTIONAL | EMAIL | `deny` on_commit |
| `transaction_cancelled` | TRANSACTIONAL | EMAIL | `cancel` on_commit |
| `transaction_expired` | TRANSACTIONAL | EMAIL | `expire` on_commit |
| `transaction_expiring_soon` | TRANSACTIONAL | EMAIL, PUSH | `send_expiration_reminder_task` |
| `transaction_info_requested` | TRANSACTIONAL | EMAIL, PUSH | `request_info` on_commit |
| `transaction_resubmitted` | TRANSACTIONAL | EMAIL | `resubmit_after_info_request` on_commit |

---

## 9. Configuration & Gotchas

### Celery Beat Schedule

| Task | Schedule | Purpose |
|------|----------|---------|
| `expire_transactions_task` | Every hour | Expire overdue transactions |
| `cleanup_old_transaction_logs_task` | Daily | Delete logs for terminal transactions older than 90 days |
| `send_expiration_reminder_task` | Daily 09:00 UTC | Remind targets of transactions expiring in 24-48 hours |
| `retry_outcome_execution_task` | On-demand (max 3 retries, 300s backoff) | Retry failed outcome execution |

### Rate Limits

| Limit | Value | TTL |
|-------|-------|-----|
| `user_requests_per_hour` | 10 | 3600s |
| `user_connection_requests_per_day` | 20 | 86400s |
| `business_invitations_per_day` | 50 | 86400s |
| `resubmissions_per_day_per_target` | 3 | 86400s |

Requires real cache backend (LocMemCache or Redis). **DummyCache in test settings makes `cache.set()` a no-op** — rate limit tests use a LocMemCache fixture override.

### Gotchas

- **SQLite UNION + ORDER BY**: SQLite disallows ORDER BY in subqueries of compound statements. In `TransactionListView`, the "all" role query must strip ordering before `.union()` and reapply after: `qs1.order_by().union(qs2.order_by()).order_by("-created_at")`
- **Lazy import mocking**: Services imported inside function bodies (`from X import Y` in the function) must be mocked at the source module (`X.Y`), not the consumer module. Affects outcome handlers and tasks that lazy-import RBACService, BusinessAccountService, NotificationService.
- **base_member_role fixture**: Accept tests that trigger `MembershipOutcomeHandler` need a `base_member_role` fixture because `RBACService.create_membership` falls back to `RoleSelector.get_base_member_role()`.
- **auto_now_add fields**: `created_at` cannot be set at creation time. Use `Model.objects.filter(id=obj.id).update(created_at=...)` after factory creation.
- **UUID serialization**: Always `str(uuid)` when storing UUIDs in JSONField or passing to serializers.
- **context_id NULL**: For `context_type="user"` transactions (e.g., `user_connection_request`), `context_id` is NULL. The CheckConstraint enforces that non-user context types always have a context_id.
- **_transition() saves all dirty fields**: `_transition()` calls `transaction.save()` without `update_fields`, so any fields modified before calling `_transition()` (like `info_requested_at/by/message/fields`) are persisted automatically. This is intentional — set all fields before calling `_transition()`.

---

## 10. Local Development

### Setup

```bash
# Already included in INSTALLED_APPS
# Run migrations
cd backend
python manage.py migrate

# Verify models
python manage.py shell -c "from apps.transaction.models import Transaction, TransactionLog; print('OK')"
```

### Test Data

- `TransactionFactory` — configurable factory for any transaction type/status
- `TransactionLogFactory` — creates log entries linked to a transaction
- Fixtures in `apps/transaction/tests/conftest.py`: `pending_invitation`, `pending_request`, `expired_transaction`, `accepted_transaction`
- Required supporting fixtures: `user`, `another_user`, `third_user`, `business`, `owner_with_invite_perm`, `member_with_approve_perm`, `base_member_role`

### Useful URLs

| URL | Method | Purpose |
|-----|--------|---------|
| `/api/v1/transactions/` | GET | List current user's transactions |
| `/api/v1/transactions/invitation/` | POST | Create an invitation |
| `/api/v1/transactions/request/` | POST | Create a request |
| `/api/v1/transactions/<uuid>/` | GET | View transaction detail |

---

## 11. Deployment

| Aspect | Local (SQLite) | Production (PostgreSQL + Redis) |
|--------|----------------|-------------------------------|
| Database | SQLite (UNION workaround active) | PostgreSQL (UNION works natively) |
| Cache | DummyCache (rate limits no-op) | Redis (rate limits enforced) |
| Celery | ALWAYS_EAGER=True (sync) | Real worker + Beat scheduler |
| Notifications | Sync in-process | Async via Celery tasks |

### Pre-Deploy Checklist

- [ ] Run migrations: `python manage.py migrate`
- [ ] Verify permission seed: `python manage.py shell -c "from apps.rbac.models import Permission; print(Permission.objects.filter(category='transaction').count())"` (should be 2)
- [ ] Verify Celery Beat config includes 3 transaction tasks
- [ ] Verify Redis is available for rate limiting
- [ ] Verify notification email templates exist for 8 transaction types

---

## 12. Testing

| Module | Tests | Status |
|--------|-------|--------|
| test_models.py | 58 | Pass |
| test_constants.py | 32 | Pass |
| test_types.py | 76 | Pass |
| test_selectors.py | 30 | Pass |
| test_policies.py | 37 | Pass |
| test_services.py | 61 | Pass |
| test_outcome_handlers.py | 11 | Pass |
| test_views.py | 22 | Pass |
| test_tasks.py | 11 | Pass |
| test_rate_limits.py | 5 | Pass |
| test_form_integration.py | 24 | Form validation, bidirectional linking, request info, resubmit, form response update, info_requested transitions |
| **Total** | **367** | **Pass** |

**Coverage:** 95.8% for `apps/transaction/`

**Test infrastructure:**
- `apps/transaction/tests/factories.py` — TransactionFactory, TransactionLogFactory
- `apps/transaction/tests/conftest.py` — 20+ fixtures (users, accounts, memberships, permissions, actor contexts, transactions, URLs)
- All tests use `@pytest.mark.django_db`, AAA pattern, factory-boy

---

## 13. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/transaction/__init__.py` | Package init |
| `apps/transaction/apps.py` | Django app config |
| `apps/transaction/constants.py` | Enums, terminal states, valid transitions |
| `apps/transaction/types.py` | 10 TransactionTypeConfig instances, get_transaction_type() |
| `apps/transaction/models.py` | Transaction and TransactionLog models |
| `apps/transaction/managers.py` | TransactionQuerySet (8 methods), TransactionManager |
| `apps/transaction/signals.py` | Placeholder for future signals |
| `apps/transaction/selectors.py` | TransactionSelector (11 methods), TransactionLogSelector |
| `apps/transaction/policies.py` | TransactionPolicy (5 authorization methods) |
| `apps/transaction/services.py` | TransactionService (10 public + 10 private methods) |
| `apps/transaction/outcome_handlers.py` | Registry + 6 handler classes, register_all_handlers() |
| `apps/transaction/rate_limits.py` | check_rate_limit() with 4 limit types |
| `apps/transaction/tasks.py` | 4 Celery tasks |
| `apps/transaction/api/__init__.py` | API package init |
| `apps/transaction/api/serializers.py` | 5 input + 3 output serializers |
| `apps/transaction/api/views.py` | 12 views + TransactionContextMixin |
| `apps/transaction/api/urls.py` | 12 URL patterns |
| `apps/transaction/migrations/0001_initial.py` | Schema migration |
| `apps/transaction/tests/__init__.py` | Test package init |
| `apps/transaction/tests/factories.py` | TransactionFactory, TransactionLogFactory |
| `apps/transaction/tests/conftest.py` | 20+ test fixtures |
| `apps/transaction/tests/test_models.py` | 58 tests |
| `apps/transaction/tests/test_constants.py` | 32 tests |
| `apps/transaction/tests/test_types.py` | 76 tests |
| `apps/transaction/tests/test_selectors.py` | 30 tests |
| `apps/transaction/tests/test_policies.py` | 37 tests |
| `apps/transaction/tests/test_services.py` | 61 tests |
| `apps/transaction/tests/test_outcome_handlers.py` | 11 tests |
| `apps/transaction/tests/test_views.py` | 22 tests |
| `apps/transaction/tests/test_tasks.py` | 11 tests |
| `apps/transaction/tests/test_rate_limits.py` | 5 tests |
| `apps/transaction/tests/test_form_integration.py` | 24 integration tests |
| `apps/transaction/migrations/0002_add_info_requested_fields.py` | Info request fields migration |

### Modified Files

| File | Change |
|------|--------|
| `apps/notifications/types.py` | Added 6 transaction notification types |
| `apps/rbac/services.py` | Implemented `transfer_ownership()` (replaced stub) |
| `apps/core/observability/audit/models.py` | Added 7 transaction audit actions |
| `apps/core/migrations/0003_alter_auditlog_action.py` | Migration for new audit actions |
| `apps/rbac/permissions/registry.py` | Added `can_view_transactions`, `can_view_all_transactions` |
| `apps/rbac/migrations/0003_seed_transaction_permissions.py` | Permission seed migration |
| `backend_core/settings/base.py` | Added `apps.transaction` to INSTALLED_APPS |
| `backend_core/urls.py` | Added transaction URL include |
| `backend_core/celery.py` | Added 3 scheduled transaction tasks |
| `apps/notifications/tests/test_selectors.py` | Updated expected type count (8→14) |
| `apps/notifications/tests/test_views.py` | Updated expected type sets (+6 types) |
| `apps/transaction/constants.py` | Added INFO_REQUESTED status, updated VALID_TRANSITIONS |
| `apps/transaction/types.py` | Added required_form_template_slug, optional_form_template_slug, requires_form, has_optional_form |
| `apps/transaction/models.py` | Added info_requested_at/by/message/fields, db_index on form_response_id |
| `apps/transaction/selectors.py` | Added get_by_form_response_id, get_form_template_for_type |
| `apps/transaction/services.py` | Added request_info, resubmit_after_info_request, _validate_form_requirement, _link_form_response |
| `apps/transaction/api/serializers.py` | Added RequestInfoInputSerializer, FormResponseUpdateInputSerializer, updated TransactionOutputSerializer |
| `apps/transaction/api/views.py` | Added TransactionFormSchemaView, TransactionRequestInfoView, TransactionResubmitView, TransactionFormResponseView |
| `apps/transaction/api/urls.py` | Added 4 URL patterns |
| `apps/notifications/types.py` | Added transaction_info_requested, transaction_resubmitted |
| `apps/core/observability/audit/models.py` | Added TRANSACTION_INFO_REQUESTED, TRANSACTION_RESUBMITTED |

---

## 14. Known Limitations

1. **3 stub outcome handlers**: ConnectionOutcomeHandler, FollowOutcomeHandler, and PermissionOutcomeHandler are stubs that log but perform no action — dependent subsystems not yet implemented
2. **No WebSocket/real-time updates**: Transaction state changes are communicated only via notifications (email/push), not real-time
3. **Rate limiting requires real cache**: Rate limits are a no-op under DummyCache (local dev default); enforced only with Redis/LocMemCache
4. **No batch operations**: Cannot bulk-accept/deny/cancel transactions
5. **Single form template per type**: Each transaction type supports at most one required and one optional form template

---

## 15. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Implement ConnectionOutcomeHandler | Requires connection/friendship subsystem | P1 |
| Implement FollowOutcomeHandler | Requires follow subsystem | P1 |
| Implement PermissionOutcomeHandler | Requires user permission grant system | P2 |
| Add WebSocket notifications | Real-time transaction state changes | P2 |
| Batch transaction operations | Admin bulk-accept/deny from dashboard | P2 |
| Transaction analytics/metrics | Prometheus counters for create/accept/deny rates | P3 |
| Email templates for 8 notification types | Currently notification sends but no rendered templates | P1 |
| Implement _notify_resubmitted | Currently a stub — needs approver notification logic | P2 |

---

## 16. Changelog

### v2 (2026-02-24)
- Form-Transaction integration: INFO_REQUESTED status, bidirectional form linking, revision tracking
- 2 new public service methods (request_info, resubmit_after_info_request) + 2 private helpers
- 4 new API views + URL patterns (FormSchema, RequestInfo, Resubmit, FormResponse)
- 2 new input serializers, updated TransactionOutputSerializer with inline form response
- 2 new selectors (get_by_form_response_id, get_form_template_for_type)
- Slug-based form template requirements on TransactionTypeConfig
- 2 new notification types, 2 new audit actions
- 24 new integration tests (367 total)

### v1 (2026-02-23)
- Initial implementation: 10 transaction types, state machine, pluggable outcome handlers
- 343 tests at 95.8% coverage
- 3 production bugs found and fixed during testing (UUID serialization, transaction rollback on token reuse, email retry persistence)
- SQLite UNION ORDER BY compatibility fix
