# Notifications App — Developer Guide

Multi-channel notification system with organization scope, RBAC integration, and Tier 1.5 permission-aware responses. Channels: email (implemented), push (stub), SMS (stub).

## Architecture

```
Two dispatch modes:

1. Direct-target (user-level):
   Caller → NotificationService.send(user, type, context, scope_type, scope_id)
     → PreferenceService.get_enabled_channels(scoped → global → defaults)
     → Feature config channel filter
     → NotificationLog (PENDING, scoped)
     → Celery task → Channel Registry → EmailChannel / PushChannel / SMSChannel
       → _resolve_final_status() → SENT / PARTIAL / FAILED

2. Org-broadcast (permission-based):
   Caller → NotificationService.send_to_org(scope_type, scope_id, type, context)
     → Resolve permissions: caller override > type config default_recipient_permissions
     → RBAC: MembershipSelector.get_users_with_permission() for each perm
     → Always include org owner (MembershipSelector.get_owner_membership())
     → Optionally exclude specific user IDs (e.g., the actor)
     → For each resolved recipient → send() with scope
```

## Hard Rules

### Sending Notifications
- IMPORTANT: Always use `NotificationService.send()` or `send_to_org()` to send notifications.
  Never call `EmailService.send()` directly for user-facing notifications.
- IMPORTANT: Every notification type MUST be registered in `types.py` `NOTIFICATION_TYPES`
  before it can be sent. Sending an unregistered type raises `NotFound`.
- IMPORTANT: If the type has `default_channels=[Channel.EMAIL]`, it MUST also have
  `email_template="template_name"`. Without it, EmailChannel returns `{"status": "skipped"}`.
- Use `force_channels=["email"]` only for critical/security notifications (password reset,
  verification) that must bypass user preferences.
- Use `async_dispatch=False` only in tests or when you need the result synchronously.
  Default is `True` (Celery task).

### Organization Scope
- IMPORTANT: Every notification carries `scope_type` and `scope_id`. These fields exist on
  both `NotificationLog` and `NotificationPreference`.
  - User-level: `scope_type="user"`, `scope_id=None` (auth, login, password, personal social)
  - Org-level: `scope_type="business"|"platform"`, `scope_id=<org UUID>` (transactions, org chat)
- IMPORTANT: `scope_type != "user"` requires `scope_id` to be non-null. Enforced by both
  Python validation in `send()` and a DB CHECK constraint on `NotificationLog`.
- Use `send()` for direct-target notifications where the caller knows the specific recipient.
  Always pass `scope_type`/`scope_id` to tag which org the notification relates to.
- Use `send_to_org()` for permission-broadcast notifications (e.g., approval requests) where
  the notification system resolves WHO receives it based on RBAC permissions + owner.

### send_to_org() — Permission-Broadcast
- IMPORTANT: `send_to_org()` requires either `recipient_permissions` (caller override) or
  `default_recipient_permissions` on the type config. If neither exists, raises `ValidationError`.
- Permission resolution: `recipient_permissions` arg > `type_config.default_recipient_permissions`.
- Recipients: all org members with ANY of the listed permissions + the org owner (always).
- `exclude_user_ids`: optional list of user IDs to skip (e.g., the actor who triggered the event).
- RBAC gating happens at **send time** (who receives), not at read time. Once a notification
  is stored in `NotificationLog`, it belongs to that user permanently.
- Scope varies by context: for `PLATFORM_AUTHORITY` transactions, scope is the platform
  account; for `ACCOUNT_AUTHORITY`, scope is the transaction's context account.

### Chat Scope Mapping
- Chat `ScopeType` uses `"global"` for unscoped conversations, but `NotificationScope` uses `"user"`.
- The mapping is defined in `ChatService._CHAT_TO_NOTIF_SCOPE`:
  - Chat `"global"` → Notification `"user"` (scope_id=None)
  - Chat `"business"` → Notification `"business"` (scope_id=UUID)
  - Chat `"platform"` → Notification `"platform"` (scope_id=UUID)

### Adding a New Notification Type
1. Add entry to `NOTIFICATION_TYPES` dict in `types.py` with all fields:
   - `name`, `display_name`, `description`, `category`
   - `default_channels` — which channels are enabled by default
   - `required_context` — keys that `context` dict must contain (validated on send)
   - `email_template` — must match an `EmailTemplate.name` in the database
   - `user_configurable` — `False` for security/auth types that users cannot disable
   - `default_recipient_permissions` — `None` for direct-target only, `["perm_code"]` for org-broadcast
2. If non-configurable, it auto-joins `MANDATORY_NOTIFICATION_TYPES` (frozenset).
3. If `default_recipient_permissions` is set, `send_to_org()` can be used for this type.
   The caller can still override permissions at call time.
4. Categories: `AUTH`, `SECURITY`, `TRANSACTIONAL`, `MARKETING`, `SOCIAL`, `SYSTEM`.

### Scoped Preferences
- `NotificationPreference` supports per-org channel overrides. A user can disable email for
  `transaction_accepted` globally but keep it enabled for a specific business.
- Resolution order in `PreferenceService.get_enabled_channels()`:
  1. Scoped preference `(user, type, scope_type, scope_id)` — if org scope provided
  2. Global user preference `(user, type, scope_type="user", scope_id=None)`
  3. Type defaults from `NotificationTypeConfig.default_channels`
- `send()` passes `scope_type`/`scope_id` through to `get_enabled_channels()` automatically.
- Partial unique constraints handle NULL scope_id:
  - `notifpref_user_type_scope_uniq`: `(user, type, scope_type, scope_id)` WHERE scope_id IS NOT NULL
  - `notifpref_user_type_global_uniq`: `(user, type, scope_type)` WHERE scope_id IS NULL

### Status Resolution
- IMPORTANT: All status resolution goes through `_resolve_final_status()` in
  `notification_service.py`. Never inline status logic in tasks or dispatch methods.
- Rules: "skipped" channels are excluded from the check. Empty or all-skipped → SENT.
  All effective sent → SENT. Mixed → PARTIAL. All failed → FAILED.

### Channel Implementation
- Channels live in `services/channels/`. Each inherits `BaseChannel` with a `send()` method.
- `send()` returns `{"status": "sent"|"failed"|"skipped", ...}`. Never raise — return a dict.
- If `send()` raises, the caller (tasks.py) catches and converts to `{"status": "failed"}`.
- Registry in `services/channels/__init__.py` — add new channels there.
- Push and SMS are stubs returning `{"status": "skipped"}`. Implement when ready.

### Preferences
- `NotificationPreference` stores OVERRIDES only. No record = use type defaults.
- Both `update_preference()` and `reset_preference()` reject non-configurable types.
- Preference hierarchy: Scoped Preference → Global User Preference → Type Default → Deployment Feature Config.

### RBAC & Tier 1.5
- `NotificationPolicy` in `policies.py` provides:
  - `can_view_scoped_notifications()` — membership check for org scope access
  - `can_manage_notifications()` — requires `can_manage_notifications` RBAC permission
  - `get_viewer_permissions()` — returns `_permissions` dict for Tier 1.5
- `NotificationHistoryView` uses `PermissionInjectMixin` + `policy_class = NotificationPolicy`.
  `_permissions` is injected only when `scope_id` query param is provided (org-scoped requests).
- Non-member requesting org-scoped notifications gets an empty list (not 403).
- RBAC permission `can_manage_notifications` is seeded in `rbac/migrations/0012`.
  Not assigned to any role by default — add via admin or future migration.

### Tasks (Celery)
- `dispatch_notification_task` — async dispatch with `select_for_update()` idempotency.
  Has `autoretry_for=(Exception,)` for infrastructure errors. Channel-level exceptions
  are caught per-channel (won't retry the whole task for one channel failure).
- `retry_partial_notification_task` — retries only failed channels. Max 2 retries, 5 min delay.
- `cleanup_old_notification_logs` — deletes logs older than `NOTIFICATION_LOG_RETENTION_DAYS` (90).

### Feature Gate Integration (SG/FG/VG)
- IMPORTANT: Notifications are fully integrated with the Feature Gate system.
- **System Gate (SG):** `systems.notifications` in `deployment_config.json`. When `false`:
  URLs return 404, tasks early-return, admin hidden. Blocks ALL notifications including auth.
- **Feature Gate (FG):** `user.notifications.enabled` / `business.notifications.enabled` /
  `platform.notifications.enabled`. When `false`: `send()` skips non-critical notifications
  (returns None), `send_to_org()` returns `[]`. Mandatory types (verify_email, password_reset,
  password_changed, welcome, suspicious_activity) are NEVER blocked by FG — only by SG.
- **Value Gate (VG):** Channel toggles (`notifications.email_enabled`, `notifications.push_enabled`,
  `notifications.sms_enabled`) and `notifications.log_retention_days` (default 90).
  Push defaults to `False`, SMS defaults to `False`.
- URL group file: `backend_core/urls/notifications.py` (conditionally imported by coordinator).
- Admin: conditionally registered in `apps.py` `ready()` based on SG.

## API Endpoints

| Endpoint | Methods | Purpose |
|---|---|---|
| `/api/v1/notifications/preferences/` | GET | All preferences grouped by category |
| `/api/v1/notifications/preferences/{type}/` | GET, PATCH, DELETE | Single preference CRUD |
| `/api/v1/notifications/history/` | GET | Notification log (filters: type, status, limit, offset, scope_type, scope_id) |
| `/api/v1/notifications/scopes/` | GET | Distinct scopes with notification counts (for sidebar badges) |
| `/api/v1/notifications/types/` | GET | Configurable notification types |

### History Query Parameters
- `notification_type` — filter by type name
- `status` — filter by status (pending, sent, failed, partial, retrying, processing)
- `limit` — max results, 1-100, default 50 (invalid values degrade to default)
- `offset` — skip N results, default 0
- `scope_type` — filter by scope (user, business, platform)
- `scope_id` — filter by org UUID (required with business/platform scope_type)

When `scope_id` is provided, the response includes `_permissions` (Tier 1.5).

## Models

### NotificationPreference
- Per-user channel overrides, optionally scoped per org.
- `CASCADE` on user delete. Fields: user, notification_type, scope_type, scope_id,
  email_enabled, push_enabled, sms_enabled.
- Partial unique constraints: `(user, type, scope_type, scope_id)` WHERE scope_id IS NOT NULL,
  `(user, type, scope_type)` WHERE scope_id IS NULL.

### NotificationLog
- Immutable delivery audit log, scoped to an org.
- UUID PK. `SET_NULL` on user delete.
- Fields: user, notification_type, scope_type, scope_id, channels, context, status,
  retry_count, channel_results, error_message.
- Status: PENDING → PROCESSING → SENT / PARTIAL / FAILED / RETRYING.
- CHECK constraint: `scope_type="user" OR scope_id IS NOT NULL`.
- Indexes: `(user, created_at)`, `(type, created_at)`, `(status, created_at)`,
  `(scope_type, scope_id, user, created_at)`, `(scope_type, scope_id, created_at)`.

## File Layout

```
apps/notifications/
├── constants.py           # NotificationScope enum (user, business, platform)
├── models.py              # NotificationPreference, NotificationLog (scope_type + scope_id)
├── types.py               # NotificationTypeConfig registry (27 types, 6 categories)
├── policies.py            # NotificationPolicy (RBAC + Tier 1.5)
├── views.py               # 5 API views (preferences, history, scopes, types)
├── serializers.py         # DRF serializers (6 serializers)
├── selectors.py           # Read-only queries (scope filtering, scope summary)
├── tasks.py               # Celery: dispatch, retry, cleanup
├── urls.py                # 5 URL patterns
├── admin.py               # Admin (log is read-only, scope in list_display)
├── services/
│   ├── notification_service.py  # send(), send_to_org(), send_bulk(), _dispatch_now()
│   ├── preference_service.py    # get/update/reset preferences (scoped resolution)
│   └── channels/
│       ├── base.py              # BaseChannel ABC
│       ├── email_channel.py     # EmailChannel (implemented)
│       ├── push_channel.py      # PushChannel (stub)
│       └── sms_channel.py       # SMSChannel (stub)
└── tests/                 # 180 tests
    ├── conftest.py
    ├── factories.py       # Includes ScopedNotificationLogFactory, ScopedPreferenceFactory
    ├── test_models.py
    ├── test_services.py
    ├── test_selectors.py
    ├── test_tasks.py
    ├── test_views.py
    └── test_policies.py   # RBAC + Tier 1.5 tests
```

## Common Gotchas
- `_resolve_final_status()` is the SINGLE source of truth for status logic. The same
  function is used by `_dispatch_now()`, `dispatch_notification_task`, and
  `retry_partial_notification_task`. Do not duplicate or inline.
- `channel.send()` calls in tasks are wrapped in try/except. If you add a new channel,
  do NOT rely on exceptions for flow control — always return a status dict.
- `EmailTemplate` records are DB-managed (admin/migration), not code-defined. Adding
  `email_template="name"` in types.py only works if the matching DB row exists.
- History endpoint validates `limit` (1-100), `offset` (>=0), and `status` (valid choices).
  Invalid values degrade gracefully to defaults — no 500 errors.
- `NotificationPreferenceSelector.get_users_with_channel_enabled()` returns a QuerySet
  (lazy), not a list. Callers can chain filters or iterate without loading all users.
- `transaction.on_commit()` is used by callers (auth, chat) to defer notification sends
  until the DB transaction commits. This prevents notifications for rolled-back operations.
- In tests, use `async_dispatch=False` or mock `dispatch_notification_task.delay` —
  Celery tasks don't execute in pytest without `CELERY_TASK_ALWAYS_EAGER=True`.
- `send()` passes `scope_type`/`scope_id` through to `PreferenceService.get_enabled_channels()`.
  If you bypass `send()` and call `get_enabled_channels()` directly, you must pass scope params
  yourself or scoped preferences won't be consulted.
- `send_to_org()` requires either `recipient_permissions` (caller arg) or
  `default_recipient_permissions` (type config). If both are `None`/empty, it raises
  `ValidationError` — it does NOT silently skip.
- Chat `ScopeType.GLOBAL` = `"global"` but `NotificationScope` has no `"global"` value.
  Always use `_CHAT_TO_NOTIF_SCOPE` mapping in `ChatService` when passing scope from
  conversations to notifications.
- The `notifpref_user_type_uniq` constraint was replaced by two partial constraints in
  migration 0003. The old constraint name no longer exists — do not reference it.
