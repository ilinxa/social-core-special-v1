# Network System — Backend Implementation Reference

**Version:** v3
**Last Updated:** 2026-03-10
**Status:** Implemented
**Plan:** `C:\Users\AsiaData\.claude\plans\polymorphic-riding-backus.md`

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     API Layer (views.py)                      │
│  FollowCreateView  FollowDeleteView  FollowingListView       │
│  UserConnectionRequestView  UserConnectionDeleteView         │
│  UserConnectionListView  BusinessFollowersListView           │
│  BusinessFollowerRemoveView  BusinessConnectionListView      │
│  BusinessConnectionRequestView  BusinessConnectionDeleteView │
│  UserNetworkStatsView  BusinessNetworkStatsView              │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                    Serializers (serializers.py)               │
│  FollowCreateInput  FollowOutput  FollowingOutput            │
│  UserConnectionRequestInput  UserConnectionOutput            │
│  BusinessConnectionRequestInput  AccountConnectionOutput     │
│  NetworkStatsOutput  NetworkUserOutput                       │
└────────────────────────────┬─────────────────────────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Services   │   │    Selectors     │   │    Policies      │
│ FollowSvc   │   │ FollowSelector   │   │ NetworkPolicy    │
│ ConnectionSvc│  │ ConnectionSelector│  │ (can_follow,     │
│ (writes)    │   │ (reads)          │   │  can_connect...) │
└──────┬──────┘   └────────┬─────────┘   └──────────────────┘
       │                   │
┌──────▼───────────────────▼─────────────────────────────────┐
│                     Models (models.py)                       │
│  Follow (User → Business/Platform, polymorphic followee)    │
│  Connection (User ↔ User, Account ↔ Account, canonical)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐   ┌───────────────┐   ┌───────────────┐
│ Transaction │   │    RBAC       │   │ Notification  │
│ System      │   │ (permissions) │   │ System        │
│ (outcome    │   │ can_manage_   │   │ (5 social     │
│  handlers)  │   │ followers/    │   │  types)       │
│             │   │ connections   │   │               │
└─────────────┘   └───────────────┘   └───────────────┘
```

The Network system is the 9th Django app. It handles **follows** (one-way: User → Business/Platform) and **connections** (two-way: User ↔ User, Account ↔ Account). All state transitions are routed through the Transaction system — the Network app owns the persistence layer (Follow/Connection models) and outcome handlers that create records when transactions reach accepted state.

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Base model classes | `UUIDModel + TimeStampedModel` (NOT AuditModel/SoftDeleteModel) | Follow/Connection use explicit `status` field for lifecycle; soft delete would be redundant |
| Follow followee reference | Polymorphic `followee_type` + `followee_id` (not FK) | Consistent with Transaction's `target_type`/`target_id` pattern; supports Business and Platform |
| Single Connection model | `connection_type` discriminator with nullable user/account fields | Shared lifecycle logic; CHECK constraints enforce field presence per type; avoids UNION queries |
| Two types for business follows | `business_follow_request` (AUTO) + `business_follow_approval_request` (ACCOUNT_AUTHORITY) | `TransactionPolicy.can_accept()` raises for AUTO_APPROVAL — can't reuse single type for both public and private businesses |
| Canonical ordering | `str(id_a) <= str(id_b)` in service layer | Prevents duplicate connections regardless of which user initiates; Django CHECK constraints on FK UUIDs are awkward |
| Business connections use USER initiator | `initiator_types=[USER]` with business info in `payload` | `create_request()` hardcodes `initiator_type=PartyType.USER` — cannot use MEMBERSHIP_ACTOR for requests |
| Outcome handlers in `apps.network` | Not in `apps.transaction` | Ownership principle — network owns its persistence logic |
| `_relationship` uses status strings | `follow_status: str\|null` not `is_following: bool` | Consistent with existing `membership_status: str\|null` pattern |

## 3. Data Layer

### 3.1 Follow

Location: `apps/network/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `follower` | FK(User, CASCADE) | `related_name='follows'` |
| `followee_type` | CharField(20) | Choices: `business`, `platform`. Indexed |
| `followee_id` | UUIDField | Indexed. Polymorphic reference |
| `status` | CharField(20) | Choices: `active`, `removed`. Default: `active`. Indexed |
| `removed_at` | DateTimeField | Nullable |
| `removed_by` | FK(User, SET_NULL) | Nullable. `related_name='removed_follows'` |
| `created_at` | DateTimeField | From `TimeStampedModel`, `auto_now_add=True` |
| `updated_at` | DateTimeField | From `TimeStampedModel`, `auto_now=True` |

**Constraints:**
- `unique_active_follow`: UNIQUE(`follower`, `followee_type`, `followee_id`) WHERE `status='active'`

**Indexes:**
- (`follower`, `followee_type`, `followee_id`) — lookup by user+entity
- (`followee_type`, `followee_id`, `status`) — list followers of an entity
- (`follower`, `status`) — list following for a user

### 3.2 Connection

Location: `apps/network/models.py`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | From `UUIDModel` |
| `connection_type` | CharField(20) | Choices: `user_user`, `account_account`. Indexed |
| `user_a` | FK(User, CASCADE, null) | Canonical: `str(user_a.id) < str(user_b.id)` |
| `user_b` | FK(User, CASCADE, null) | |
| `account_a_type` | CharField(20) | Blank, default="" |
| `account_a_id` | UUIDField(null) | |
| `account_b_type` | CharField(20) | Blank, default="" |
| `account_b_id` | UUIDField(null) | |
| `status` | CharField(20) | Choices: `active`, `disconnected`. Default: `active`. Indexed |
| `note` | TextField | Blank. Connection request message |
| `initiated_by` | FK(User, SET_NULL, null) | Who initiated the request |
| `connected_at` | DateTimeField(null) | When the connection became active |
| `disconnected_at` | DateTimeField(null) | |
| `disconnected_by` | FK(User, SET_NULL, null) | |

**Constraints:**
- `unique_active_user_connection`: UNIQUE(`user_a`, `user_b`) WHERE `status='active'` AND `connection_type='user_user'`
- `unique_active_account_connection`: UNIQUE(`account_a_type`, `account_a_id`, `account_b_type`, `account_b_id`) WHERE `status='active'` AND `connection_type='account_account'`
- `user_connection_requires_users`: CHECK — `user_user` type requires both `user_a` and `user_b` NOT NULL
- `account_connection_requires_accounts`: CHECK — `account_account` type requires both `account_a_id` and `account_b_id` NOT NULL

**Indexes:**
- (`user_a`, `user_b`, `status`)
- (`account_a_type`, `account_a_id`, `status`)
- (`account_b_type`, `account_b_id`, `status`)

### Migrations

- `0001_initial` — Creates `network_follow` and `network_connection` tables with all constraints and indexes
- `apps/rbac/migrations/0008_seed_network_permissions.py` — Seeds `can_manage_followers` and `can_manage_connections` RBAC permissions

## 4. Service Layer

### 4.1 FollowService

Location: `apps/network/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_follow` | `follower, followee_type, followee_id, transaction_id?, request?` | `Follow` | Reactivates removed follows. Raises `ConflictError` if already active. Audit: `FOLLOW_CREATED` |
| `unfollow` | `follow_id, user, request?` | `Follow` | Validates `follower==user`. Sets `status=REMOVED`. Audit: `FOLLOW_REMOVED` |
| `remove_follower` | `follow_id, actor, actor_context, request?` | `Follow` | RBAC check `can_manage_followers`. Audit: `FOLLOWER_REMOVED`. Sends notification |

### 4.2 ConnectionService

Location: `apps/network/services.py`

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `_canonical_user_pair` | `user_a_id, user_b_id` | `tuple[UUID, UUID]` | Ensures `str(a) <= str(b)` |
| `_canonical_account_pair` | `a_type, a_id, b_type, b_id` | `tuple` | Ensures `(a_type, str(a_id)) <= (b_type, str(b_id))` |
| `create_user_connection` | `user_a_id, user_b_id, note, initiated_by_id, transaction_id?, request?` | `Connection` | Canonical order. Reactivates disconnected. Audit: `CONNECTION_CREATED` |
| `create_account_connection` | `a_type, a_id, b_type, b_id, initiated_by_id, note, transaction_id?, request?` | `Connection` | Same pattern for accounts. Audit: `CONNECTION_CREATED` |
| `disconnect_user_connection` | `connection_id, user, request?` | `Connection` | Validates user is party. Raises `BusinessRuleViolation` for wrong type. Audit: `CONNECTION_DISCONNECTED` |
| `disconnect_account_connection` | `connection_id, actor, actor_context, request?` | `Connection` | RBAC check on at least one side. Audit: `CONNECTION_DISCONNECTED` |

All write methods: `@staticmethod`, `@transaction.atomic`, keyword-only args.

### 4.3 Selectors

Location: `apps/network/selectors.py`

**FollowSelector** (7 methods):

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_by_id` | `follow_id` | `Follow` | Raises `NotFound` |
| `is_following` | `follower_id, followee_type, followee_id` | `bool` | Active follows only |
| `get_follow_for_user` | `follower_id, followee_type, followee_id` | `Follow\|None` | Any status, newest first |
| `get_followers` | `followee_type, followee_id` | `QuerySet` | Active, `select_related('follower')` |
| `get_following` | `user_id, followee_type?` | `QuerySet` | Optional type filter |
| `count_followers` | `followee_type, followee_id` | `int` | Active count |
| `count_following` | `user_id` | `int` | Active count |

**ConnectionSelector** (9 methods):

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_by_id` | `connection_id` | `Connection` | Raises `NotFound` |
| `is_connected` | `user_a_id, user_b_id` | `bool` | Uses canonical ordering internally |
| `is_connected_account` | `a_type, a_id, b_type, b_id` | `bool` | Canonical ordering |
| `get_user_connections` | `user_id, status?` | `QuerySet` | `Q(user_a=id) \| Q(user_b=id)`, `select_related` |
| `get_account_connections` | `account_type, account_id, status?` | `QuerySet` | Both sides |
| `count_user_connections` | `user_id` | `int` | Active |
| `count_account_connections` | `account_type, account_id` | `int` | Active |
| `get_mutual_connections` | `user_a_id, user_b_id` | `QuerySet[User]` | Intersection of both users' connections |
| `get_connection_between_users` | `user_a_id, user_b_id` | `Connection\|None` | Any status, canonical order |

## 5. API Layer

### 5.1 Endpoints

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/api/v1/network/follow/` | POST | IsAuthenticated | Create follow (routes to appropriate transaction type) |
| `/api/v1/network/follow/<uuid>/` | DELETE | IsAuthenticated | Unfollow |
| `/api/v1/network/following/` | GET | IsAuthenticated | List accounts user follows (paginated, `?type=` filter) |
| `/api/v1/network/connections/request/` | POST | IsAuthenticated | Send user connection request (creates transaction) |
| `/api/v1/network/connections/<uuid>/` | DELETE | IsAuthenticated | Disconnect from user |
| `/api/v1/network/connections/` | GET | IsAuthenticated | List user's connections (paginated, `?status=` filter) |
| `/api/v1/network/business/<slug>/followers/` | GET | IsAuthenticated | List business followers (paginated) |
| `/api/v1/network/business/<slug>/followers/<uuid>/` | DELETE | IsAuthenticated | Remove a follower (RBAC: `can_manage_followers`) |
| `/api/v1/network/business/<slug>/connections/` | GET | IsAuthenticated | List business connections (paginated) |
| `/api/v1/network/business/<slug>/connections/request/` | POST | IsAuthenticated | Request business connection (RBAC: `can_manage_connections`) |
| `/api/v1/network/business/<slug>/connections/<uuid>/` | DELETE | IsAuthenticated | Disconnect business connection (RBAC: `can_manage_connections`) |
| `/api/v1/network/stats/` | GET | IsAuthenticated | User network stats (following_count, connections_count) |
| `/api/v1/network/business/<slug>/stats/` | GET | IsAuthenticated | Business network stats (followers_count, connections_count) |

### 5.2 Serializers

Location: `apps/network/serializers.py`

| Serializer | Type | Fields | Notes |
|------------|------|--------|-------|
| `FollowCreateInput` | Input | `followee_type`, `followee_id` | ChoiceField for type |
| `UserConnectionRequestInput` | Input | `target_user_id`, `note?` | Note max_length=500 |
| `BusinessConnectionRequestInput` | Input | `target_account_type`, `target_account_id`, `note?` | |
| `NetworkUserOutput` | Embedded | `id`, `username`, `display_name`, `avatar_url` | Slim user repr |
| `FollowOutput` | Output | `id`, `follower{}`, `followee_type`, `followee_id`, `followee_name`, `status`, `created_at` | Follower list items |
| `FollowingOutput` | Output | `id`, `followee_type`, `followee_id`, `followee_name`, `followee_slug`, `created_at` | Following list items |
| `UserConnectionOutput` | Output | `id`, `other_user{}`, `note`, `status`, `connected_at`, `created_at` | Resolves other_user from viewer context |
| `AccountConnectionOutput` | Output | `id`, `other_account{type,id,name}`, `note`, `status`, `connected_at`, `created_at` | Resolves other_account from viewer context |
| `NetworkStatsOutput` | Output | `followers_count`, `following_count`, `connections_count` | |

Helper functions `_resolve_followee_name()`, `_resolve_followee_slug()`, `_resolve_account_name()` lazily resolve polymorphic references to display names/slugs.

### 5.3 Key View Logic

**FollowCreateView** (`POST /follow/`):
- `followee_type == "platform"` → `platform_follow_request` (AUTO_APPROVAL → immediate follow)
- `followee_type == "business"` + `profile.is_public == True` → `business_follow_request` (AUTO_APPROVAL)
- `followee_type == "business"` + `profile.is_public == False` → `business_follow_approval_request` (ACCOUNT_AUTHORITY → pending)

**BusinessConnectionRequestView** (`POST /business/<slug>/connections/request/`):
- Validates user has `can_manage_connections` on the business (RBAC check in view)
- Builds payload with `initiator_account_type`, `initiator_account_id`, `note`
- Target business → `business_connection_request`; target platform → `business_platform_connection_request`
- `create_request()` uses user_id as initiator; business identity is in payload

## 6. Transaction Types

### Modified Existing Types

| Type | Change |
|------|--------|
| `business_follow_request` | Added `conflict_group="business_follow"`, updated `outcome_handler` to `apps.network.outcome_handlers.FollowOutcomeHandler.handle_accepted` |
| `user_connection_request` | Added `conflict_group="user_connection"`, `payload_schema` (note), `resubmission_cooldown_days=7`, updated `outcome_handler` |

### New Types (4)

| Type ID | Mode | Approver | Conflict Group | Outcome Handler |
|---------|------|----------|----------------|-----------------|
| `business_follow_approval_request` | REQUEST | ACCOUNT_AUTHORITY | `business_follow` | `FollowOutcomeHandler.handle_accepted` |
| `platform_follow_request` | REQUEST | AUTO_APPROVAL | — | `FollowOutcomeHandler.handle_accepted` |
| `business_connection_request` | REQUEST | ACCOUNT_AUTHORITY | `business_connection` | `ConnectionOutcomeHandler.handle_account_accepted` |
| `business_platform_connection_request` | REQUEST | PLATFORM_AUTHORITY | — | `ConnectionOutcomeHandler.handle_account_accepted` |

All network types: `category="social"`, `expiration_days=30`, no form requirements.
Connection types: `resubmission_cooldown_days=7`, `approval_permission="can_manage_connections"`.
`business_follow_approval_request`: `approval_permission="can_manage_followers"`.

**Total transaction types: 14** (was 10).

## 7. Outcome Handlers

Location: `apps/network/outcome_handlers.py`

| Handler | Method | Trigger | Creates |
|---------|--------|---------|---------|
| `FollowOutcomeHandler` | `handle_accepted` | Follow txn accepted | `Follow` record via `FollowService.create_follow()` |
| `ConnectionOutcomeHandler` | `handle_user_accepted` | User↔User connection accepted | `Connection` (user_user) via `ConnectionService.create_user_connection()` |
| `ConnectionOutcomeHandler` | `handle_account_accepted` | Account↔Account connection accepted | `Connection` (account_account) via `ConnectionService.create_account_connection()`. Reads `initiator_account_type`/`id` from transaction payload |

Handlers are registered in `apps/transaction/outcome_handlers.py` → `register_all_handlers()`.
Previous stub handlers in the transaction app were removed.

## 8. Key Flows

### Flow 1: Follow a Public Business
1. User sends `POST /network/follow/` with `{followee_type: "business", followee_id: uuid}`
2. View checks `business.profile.is_public` → True
3. Creates `business_follow_request` transaction via `TransactionService.create_request()`
4. Transaction auto-approves (AUTO_APPROVAL): CREATED → PENDING → ACCEPTED synchronously
5. `FollowOutcomeHandler.handle_accepted()` fires → `FollowService.create_follow()`
6. Follow record created. Response: `{transaction_id, status: "accepted"}`

### Flow 2: Follow a Private Business
1. Same POST as above, but `is_public == False`
2. Creates `business_follow_approval_request` (ACCOUNT_AUTHORITY)
3. Transaction stays PENDING. Response: `{transaction_id, status: "pending"}`
4. Business manager accepts via `POST /transactions/<id>/accept/`
5. `FollowOutcomeHandler.handle_accepted()` fires → Follow record created

### Flow 3: User Connection Request
1. User sends `POST /network/connections/request/` with `{target_user_id, note?}`
2. Creates `user_connection_request` transaction (TARGET_ACCEPTANCE)
3. Transaction stays PENDING. Target user must accept
4. Target accepts → `ConnectionOutcomeHandler.handle_user_accepted()`
5. Connection created with canonical ordering (`str(user_a.id) <= str(user_b.id)`)

### Flow 4: Business Connection Request
1. Business manager sends `POST /network/business/<slug>/connections/request/` with `{target_account_type, target_account_id, note?}`
2. View validates user has `can_manage_connections` RBAC permission
3. Payload includes `initiator_account_type`/`id` (business identity)
4. Creates `business_connection_request` or `business_platform_connection_request`
5. Target account authority accepts → `ConnectionOutcomeHandler.handle_account_accepted()`
6. Account connection created with canonical ordering

### Flow 5: Unfollow / Disconnect
1. **Unfollow**: `DELETE /network/follow/<uuid>/` → validates `follower==user` → status=REMOVED
2. **User disconnect**: `DELETE /network/connections/<uuid>/` → validates user is party → status=DISCONNECTED
3. **Remove follower**: `DELETE /network/business/<slug>/followers/<uuid>/` → RBAC check `can_manage_followers` → status=REMOVED + notification

## 9. Permissions & Authorization

| Action | RBAC Permission | Audit Action | Notes |
|--------|----------------|--------------|-------|
| Create follow | (none — via transaction system) | `FOLLOW_CREATED` | Transaction handles authorization |
| Unfollow | (follower identity check) | `FOLLOW_REMOVED` | Must be the follower |
| Remove follower | `can_manage_followers` | `FOLLOWER_REMOVED` | Business/platform managers |
| Accept follow request | `can_manage_followers` | (via transaction) | For private business follows |
| Create connection | (none — via transaction system) | `CONNECTION_CREATED` | |
| Disconnect user | (party identity check) | `CONNECTION_DISCONNECTED` | Must be either user |
| Disconnect account | `can_manage_connections` | `CONNECTION_DISCONNECTED` | On at least one side |
| Accept connection request | `can_manage_connections` | (via transaction) | For account connections |

### RBAC Permissions (seeded via migration 0008)

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_manage_followers` | Manage Followers | network | `business`, `platform_only` |
| `can_manage_connections` | Manage Connections | network | `business`, `platform_only` |

### Tier 1.5 Permissions (injected into GET detail responses)

**Business detail** (`_permissions`):
- `can_follow`, `can_unfollow`, `can_manage_followers`, `can_manage_connections`

**User detail** (`_permissions`):
- `can_connect`, `can_disconnect`

### `_relationship` Injection

**Business/Platform detail** (`_relationship`):
- `follow_status: str|null` — `"active"`, `"removed"`, or `null`
- `follow_id: str|null` — UUID of the Follow record (needed for `DELETE /network/follow/{id}/`)
- `active_follow_transaction: {id, type, status, mode, viewer_role}|null` — pending follow request; `viewer_role` is `"initiator"` or `"target"`

**User detail** (`_relationship`):
- `connection_status: str|null` — `"active"`, `"disconnected"`, or `null`
- `connection_id: str|null` — UUID of the Connection record (needed for `DELETE /network/connections/{id}/`)
- `active_connection_transaction: {id, type, status, mode, viewer_role}|null` — pending connection request; `viewer_role` is `"initiator"` or `"target"`

**`viewer_role` logic:** `"initiator" if txn.initiator_id == viewer.id else "target"` — determines whether the frontend shows "Cancel Request" (initiator) or "Accept/Decline" (target).

## 10. Notification Types

Location: `apps/notifications/types.py` — SOCIAL category

| Type | Category | Channels | Configurable |
|------|----------|----------|-------------|
| `new_follower` | social | push | Yes |
| `follow_request_received` | social | push, email | Yes |
| `follow_request_accepted` | social | push | Yes |
| `connection_request_received` | social | push, email | Yes |
| `connection_accepted` | social | push | Yes |

## 11. Configuration & Gotchas

### Gotchas

- **Canonical ordering in tests**: Factories must sort users before creating connections — `a, b = sorted([user_a, user_b], key=lambda u: str(u.id))`. Selectors assume canonical order.
- **Factory import path**: Use `apps.organization.tests.factories` NOT `apps.organization.business.tests.factories` (no `tests/` subpackage in business/)
- **RBACService initialization**: `RBACService.initialize_business_account(business_id=biz.id, ...)` NOT `business=biz`
- **Lazy imports in views**: Mock at source module (`@patch("apps.transaction.services.TransactionService")`), NOT consumer module
- **Outcome handlers create real DB records**: Tests using `TransactionFactory(type="user_connection_request")` must supply real user IDs via `UserFactory()` (FK constraint)
- **CHECK constraints**: Can't mutate `connection_type` in tests (e.g., setting `user_user` connection to `account_account`) — CHECK fires because account fields are NULL. Use the correct factory type instead.
- **Business connections use USER initiator**: `create_request()` hardcodes `initiator_type=PartyType.USER`. Business identity is in `payload.initiator_account_type`/`initiator_account_id`.
- **Serializer name resolution**: `_resolve_followee_name()` must use `biz.profile.display_name` (not `biz.name`) and `plat.profile.name` (not `plat.name`). `BusinessAccount` has `legal_name`, not `name`; display name lives on `BusinessProfile`. Same for `_resolve_account_name()`.
- **`_build_relationship_data()` target filter**: When filtering connection transactions on user detail view, must check both `target_id == target.id OR initiator_id == target.id` — the profile being viewed could be either party in the transaction.

## 12. Testing

| Module | Tests | Status |
|--------|-------|--------|
| `test_models.py` | 14 | Pass |
| `test_selectors.py` | 24 | Pass |
| `test_services.py` | 14 | Pass |
| `test_policies.py` | 14 | Pass |
| `test_outcome_handlers.py` | 4 | Pass |
| `test_views.py` | 22 | Pass |
| `_relationship` tests (business/platform/user views) | 7 | Pass |
| **Total** | **99** | **All pass** |

Factories: `FollowFactory`, `UserConnectionFactory`, `AccountConnectionFactory` in `apps/network/tests/factories.py`.

Test conftest (`apps/network/tests/conftest.py`): `api_client`, `user`, `user_b`, `user_c`, `authenticated_client` (force_authenticate), `business` (with profile + RBAC init), `private_business`, `platform`.

## 13. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/network/__init__.py` | Empty |
| `apps/network/apps.py` | `NetworkConfig` |
| `apps/network/models.py` | Follow + Connection models with 4 enums |
| `apps/network/selectors.py` | FollowSelector (7 methods) + ConnectionSelector (9 methods) |
| `apps/network/services.py` | FollowService (3 methods) + ConnectionService (6 methods) |
| `apps/network/policies.py` | NetworkPolicy (9 methods including Tier 1.5 helpers) |
| `apps/network/outcome_handlers.py` | FollowOutcomeHandler + ConnectionOutcomeHandler |
| `apps/network/serializers.py` | 3 input + 5 output serializers + 3 resolver helpers |
| `apps/network/views.py` | 13 view classes |
| `apps/network/urls.py` | 13 URL patterns |
| `apps/network/admin.py` | FollowAdmin + ConnectionAdmin |
| `apps/network/migrations/0001_initial.py` | Schema migration |
| `apps/rbac/migrations/0008_seed_network_permissions.py` | Seeds 2 RBAC permissions |
| `apps/network/tests/factories.py` | 3 factories |
| `apps/network/tests/conftest.py` | 8 fixtures |
| `apps/network/tests/test_models.py` | 14 model tests |
| `apps/network/tests/test_selectors.py` | 24 selector tests |
| `apps/network/tests/test_services.py` | 14 service tests |
| `apps/network/tests/test_policies.py` | 14 policy tests |
| `apps/network/tests/test_outcome_handlers.py` | 4 outcome handler tests |
| `apps/network/tests/test_views.py` | 22 view tests |

### Modified Files

| File | Change |
|------|--------|
| `apps/transaction/types.py` | Added 4 new types, modified 2 existing (conflict groups, handler paths, payload_schema) |
| `apps/transaction/outcome_handlers.py` | Deleted 2 stub classes, updated `register_all_handlers()` with 6 network handler registrations |
| `apps/core/observability/audit/models.py` | Added 5 `AuditLog.Action` entries (FOLLOW_CREATED, FOLLOW_REMOVED, FOLLOWER_REMOVED, CONNECTION_CREATED, CONNECTION_DISCONNECTED) |
| `apps/rbac/permissions/registry.py` | Added 2 permissions to PERMISSIONS list (`can_manage_followers`, `can_manage_connections`) |
| `apps/notifications/types.py` | Added `SOCIAL` category + 5 notification types |
| `apps/organization/business/views.py` | Added `follow_status` + `follow_id` + `active_follow_transaction` (with `viewer_role`) to `_build_business_relationship()` |
| `apps/organization/platform/views.py` | Added `follow_status` + `follow_id` + `active_follow_transaction` (with `viewer_role`) to `_build_platform_relationship()` |
| `apps/organization/business/policies.py` | Added 4 network permissions to `get_viewer_permissions()` (`can_follow`, `can_unfollow`, `can_manage_followers`, `can_manage_connections`) |
| `apps/users/views.py` | Added `RelationshipInjectMixin` + `connection_status`/`connection_id`/`active_connection_transaction` (with `viewer_role`) to `UserPublicDetailView` |
| `apps/users/policies.py` | Added `can_connect`/`can_disconnect` to `UserPolicy.get_viewer_permissions()` |
| `backend_core/settings/base.py` | Added `"apps.network"` to INSTALLED_APPS |
| `backend_core/urls.py` | Added `path("api/v1/network/", include("apps.network.urls"))` |
| `apps/transaction/tests/test_outcome_handlers.py` | Removed stub test classes, updated handler registration test to 14 types |
| `apps/transaction/tests/test_types.py` | Added 4 new types to ALL_TYPE_IDS, updated count to 14 |
| `apps/notifications/tests/test_selectors.py` | Added 5 social types to expected sets |
| `apps/notifications/tests/test_views.py` | Added 5 social types to expected sets |

## 14. Known Limitations

1. **No N+1 query optimization for serializer name resolution**: `_resolve_followee_name()` and `_resolve_account_name()` make individual queries per item. Acceptable for paginated lists (20 items), but should use annotation/prefetch if lists grow large.
2. **Platform follow has no conflict group**: Only one type (`platform_follow_request`) exists for platform follows, so conflict group isn't needed. If a second platform follow type is added, a conflict group should be created.
3. **No `follower_removed` notification type**: The `remove_follower()` service reuses `new_follower` notification type with an `action: "removed"` context field. A dedicated type could be added if different channel routing is needed.

## 15. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Connection suggestions | "People you may know" based on mutual connections | P2 |
| Block/mute functionality | Prevent specific users from following/connecting | P2 |
| N+1 optimization | Annotate followee names in selector queryset instead of per-item resolution | P2 |
| Server-side pagination params | My Network page uses client-side filtering; add `?search=` param to selector methods for large networks | P2 |

## 16. Changelog

### v3 (2026-03-10) — E2E Bug Fixes
- **BUG**: `_resolve_followee_name()` and `_resolve_account_name()` used `biz.name`/`plat.name` which don't exist — fixed to query profile models (`biz.profile.display_name`, `plat.profile.name`) with `select_related("profile")`
- **BUG**: `UserPublicDetailView._build_relationship_data()` filtered `active_conn_txn.target_id != target.id` which excluded transactions where the viewer was the DB target — fixed to check `involves_target = target_id == target.id or initiator_id == target.id`
- **BUG** (frontend): `useRemoveBusinessFollower` only invalidated `businessFollowers` query, not `businessStats` — follower count in header stayed stale after removal. Added `businessStats` invalidation
- 33 E2E tests executed via MCP stealth browser (all pass). Checklist: `docs/testing/manual_ui_test_checklist.md` sections 1.16, 2.15, 4.7

### v2 (2026-03-10)
- Added `viewer_role` field (`"initiator"` | `"target"`) to all `active_*_transaction` dicts in `_relationship`
- Added `follow_id` to business/platform `_relationship` (needed for unfollow DELETE endpoint)
- Added `connection_id` to user `_relationship` (needed for disconnect DELETE endpoint)
- Added `active_follow_transaction` dict to platform `_relationship` (was missing)
- 7 new backend relationship tests (business + platform + user views)
- Frontend network UI now complete (see `docs/implementations/frontend/network-system.md`)

### v1 (2026-03-09)
- Initial implementation: Follow + Connection models, 13 API endpoints
- 4 new transaction types + 2 modified existing types
- 2 RBAC permissions, 5 audit actions, 5 notification types
- `_relationship` injection on business/platform/user detail views
- Tier 1.5 permissions on business and user detail views
- 92 unit tests (all passing)
- Compliance audit: 100% alignment with plan after 5 post-audit fixes
