# Deployment Configuration Guide

> How to configure the platform for different deployment scenarios.
> For the technical implementation, see `docs/implementations/backend/feature-gate-system.md`.

---

## 1. Quick Start

The platform is controlled by a JSON configuration file. Three deployment profiles are supported:

| Profile | `org_mode` | Systems | Use Case |
|---------|-----------|---------|----------|
| **Minimal** | `"user_only"` | explore, network, chat | Social network without business/platform features |
| **Community** | `"user_and_platform"` | All 6 | Forum/community with platform management, no business |
| **Full** | `"full"` | All 6 | SaaS: business accounts, platform management, all features |

To get started:
1. Copy one of the example configs from Section 8
2. Save as `deployment_config.json` in the backend root
3. Set `DEPLOYMENT_CONFIG_PATH` in your Django settings (already configured in `local_docker.py` and `production.py`)
4. Start the server

---

## 2. Configuration File

### Location

The config file path is set via the Django setting `DEPLOYMENT_CONFIG_PATH`:

```python
# backend_core/settings/base.py
DEPLOYMENT_CONFIG_PATH = BASE_DIR / "deployment_config.json"
```

Override per environment:
```python
# backend_core/settings/production.py
DEPLOYMENT_CONFIG_PATH = os.environ.get("DEPLOYMENT_CONFIG_PATH", BASE_DIR / "deployment_config.json")
```

### Format

Standard JSON object. All fields are optional — missing fields default to the most restrictive value.

### Missing File Behavior

If the config file is missing or invalid:
- All systems are **OFF**
- `org_mode` defaults to `"user_only"` (no business/platform)
- All feature gates default to **OFF**
- All limits default to **0** (unlimited — but features are off, so limits don't matter)
- Config values use hardcoded defaults

This is intentional: **minimal-by-default** prevents accidental feature exposure.

---

## 3. Organization Mode

The `org_mode` field controls which account types are available:

| `org_mode` | Business Accounts | Platform Accounts | Transaction Types Available |
|-----------|-------------------|-------------------|-----------------------------|
| `"full"` | Yes | Yes | All 14 types |
| `"user_and_platform"` | No | Yes | 8 types (6 business types excluded) |
| `"user_only"` | No | No | 1 type (user connection only, if network enabled) |

### Impact on URL Registration

- `"full"` → `/api/v1/business/` AND `/api/v1/platform/` registered
- `"user_and_platform"` → `/api/v1/platform/` only
- `"user_only"` → Neither business nor platform URLs registered

### Transaction Types by Org Mode

**Always available** (if `systems.transaction` enabled):
- `user_connection_request`

**Requires business** (`org_mode == "full"`):
- `business_membership_invitation`, `business_membership_request`
- `business_verification_request`, `ownership_transfer_request`
- `business_follow_approval_request`, `business_connection_request`

**Requires platform** (`org_mode in {"full", "user_and_platform"}`):
- `platform_membership_invitation`, `platform_membership_request`
- `platform_ownership_transfer_request`
- `business_creation_approval_request`
- `platform_follow_request`, `business_platform_connection_request`

---

## 4. System Toggles

The `systems` object contains 6 boolean toggles. When a system is OFF, its URLs are never registered (404), its Celery tasks short-circuit, and its admin pages are not loaded.

| System | What it Controls | Dependencies |
|--------|-----------------|--------------|
| `transaction` | Transaction state machine API, expiration/reminder tasks | Required by membership invitations, follow/connect requests |
| `forms` | Form builder API, system forms, form-transaction integration | Used by transactions with required forms |
| `network` | Follow/connect API, network stats, outcome handlers | Requires `transaction` for follow/connect requests |
| `chat` | Chat REST API, WebSocket consumer, presence, tasks | Independent |
| `cms` | Content management admin API, public content API, tasks | Independent |
| `explore` | Search/discovery API, tag suggestions | Independent |

**Notifications** is always-on (no system toggle). It has deployment-level channel toggles (`notifications.email_enabled`, etc.) but the notification API itself is always available.

### System Dependency Notes

- Disabling `transaction` while `network` is enabled: follows/connects that use transactions won't work. The network outcome handlers check `is_system_enabled("network")` — they won't register if network is off.
- Disabling `forms` while `transaction` is enabled: transactions that require forms will still work, but the form builder UI won't be available.

---

## 5. Feature Paths Reference

### User Features

| Config Path | Type | Default | What it Controls |
|-------------|------|---------|-----------------|
| `user.can_create_business` | bool | `false` | Business creation eligibility view |
| `user.can_be_member` | bool | `false` | Membership eligibility |
| `user.profile_visibility` | bool | `false` | Visibility settings view |
| `user.profile_default_public` | bool | `false` | Default profile visibility for new users |
| `user.forms` | bool | `false` | System form template access |
| `user.network.enabled` | bool | `false` | All user network views (follow, connect, etc.) |
| `user.network.connections` | bool | `false` | User-to-user connection requests |
| `user.network.follows` | bool | `false` | User follow actions |
| `user.chat.enabled` | bool | `false` | Chat participation |
| `user.chat.group` | bool | `false` | Group conversation creation |
| `user.chat.file_sharing` | bool | `false` | Attachment uploads in chat |
| `user.chat.reactions` | bool | `false` | Message reactions |
| `user.chat.search` | bool | `false` | Message search |
| `user.explore.can_explore` | bool | `false` | User search view access |
| `user.explore.search_users` | bool | `false` | User search results |
| `user.explore.search_businesses` | bool | `false` | Business search results |
| `user.explore.is_discoverable` | bool | `false` | Appear in search results |
| `user.transactions.enabled` | bool | `false` | Transaction creation |

### Business Features

| Config Path | Type | Default | What it Controls |
|-------------|------|---------|-----------------|
| `business.members.enabled` | bool | `false` | Member invitation/request POST |
| `business.members.invitations` | bool | `false` | Membership invitations |
| `business.members.requests` | bool | `false` | Membership requests |
| `business.members.custom_roles` | bool | `false` | Custom RBAC role creation |
| `business.chat.enabled` | bool | `false` | Business chat |
| `business.chat.entity` | bool | `false` | Business as chat participant |
| `business.chat.group` | bool | `false` | Business group conversations |
| `business.chat.file_sharing` | bool | `false` | Business attachment uploads |
| `business.network.enabled` | bool | `false` | All business network views |
| `business.network.followers` | bool | `false` | Business followers management |
| `business.network.connections` | bool | `false` | Business connections |
| `business.forms.enabled` | bool | `false` | Business form views |
| `business.forms.transaction_mapping` | bool | `false` | Form-transaction mapping |
| `business.cms` | bool | `false` | Business CMS access |
| `business.profile_visibility` | bool | `false` | Business visibility settings |
| `business.profile_default_public` | bool | `false` | Default business visibility |
| `business.transactions.enabled` | bool | `false` | Business transaction creation |
| `business.transactions.verification` | bool | `false` | Verification requests |
| `business.transactions.ownership_transfer` | bool | `false` | Ownership transfer |

### Platform Features

| Config Path | Type | Default | What it Controls |
|-------------|------|---------|-----------------|
| `platform.members.enabled` | bool | `false` | Platform member invitation/request |
| `platform.members.invitations` | bool | `false` | Platform membership invitations |
| `platform.members.requests` | bool | `false` | Platform membership requests |
| `platform.members.custom_roles` | bool | `false` | Platform custom roles |
| `platform.chat.enabled` | bool | `false` | Platform chat |
| `platform.chat.entity` | bool | `false` | Platform as chat participant |
| `platform.network` | bool | `false` | Platform network |
| `platform.forms` | bool | `false` | Platform form views |
| `platform.cms` | bool | `false` | CMS admin views |
| `platform.governance.business_approval` | bool | `false` | Business creation approval |
| `platform.governance.business_verification` | bool | `false` | Business verification |
| `platform.governance.approved_creators` | bool | `false` | Approved creator list |
| `platform.governance.global_moderation` | bool | `false` | Global moderation |
| `platform.transactions.ownership_transfer` | bool | `false` | Platform ownership transfer |

---

## 6. Limits Reference

All limits use `0` for unlimited. When both config and a model field define a limit, the tighter value wins.

| Config Path | Default | What it Caps | Dual-Source? |
|-------------|---------|-------------|--------------|
| `limits.max_users` | `0` | Total users in deployment | No |
| `limits.max_businesses` | `0` | Total businesses | No |
| `limits.max_businesses_per_user` | `0` | Businesses per user | No |
| `user.max_memberships` | `0` | Org memberships per user | No |
| `user.transactions.max_pending` | `0` | Pending transactions per user | No |
| `user.network.max_connections` | `0` | User connections | No |
| `user.network.max_follows` | `0` | User follows | No |
| `user.chat.max_groups` | `0` | User conversations (global scope) | No |
| `business.members.max_members` | `0` | Members per business | **Yes** — `BusinessAccount.max_members` |
| `business.members.max_roles` | `0` | Custom roles per business | No |
| `business.network.max_followers` | `0` | Business followers | No |
| `business.network.max_connections` | `0` | Business connections | No |
| `business.chat.max_groups` | `0` | Business conversations | No |
| `business.forms.max_forms` | `0` | Form templates per business | No |
| `platform.members.max_members` | `0` | Platform members | **Yes** — `PlatformAccount.max_members` |
| `platform.members.max_roles` | `0` | Platform custom roles | No |

### Dual-Source Limits

For `max_members`, the effective limit is `min(config_limit, model_limit)` where non-zero values are treated as limits and `0` means unlimited:

| Config | Model | Effective |
|--------|-------|-----------|
| 0 | 0 | Unlimited |
| 0 | 50 | 50 (model wins) |
| 100 | 0 | 100 (config wins) |
| 100 | 50 | 50 (tighter wins) |

---

## 7. Config Values Reference

These replace hardcoded constants with deployment-configurable values.

### Auth

| Path | Type | Default | Valid Range | Description |
|------|------|---------|------------|-------------|
| `auth.signup.email_password` | bool | `true` | — | Enable email+password signup |
| `auth.signup.email_verification_required` | bool | `true` | — | Require email verification |
| `auth.verification.method` | string | `"both"` | `"code"`, `"link"`, `"both"` | Verification delivery method |
| `auth.verification.code_length` | int | `6` | 4-8 | Digits in verification code |
| `auth.verification.expiry_minutes` | int | `15` | 5-60 | Verification code/link expiry |
| `auth.password_reset.method` | string | `"link"` | `"link"`, `"code"` | Reset delivery method |
| `auth.password_reset.expiry_minutes` | int | `60` | 15-1440 | Reset token expiry |
| `auth.sessions.max_per_user` | int | `5` | 1-20 | Max concurrent sessions |
| `auth.sessions.access_token_lifetime` | int | `900` | 300-3600 | Access token TTL (seconds) |
| `auth.sessions.refresh_token_lifetime` | int | `604800` | 3600-2592000 | Refresh token TTL (seconds) |
| `auth.lockout.max_failed_attempts` | int | `10` | 3-50 | Failed logins before lockout |
| `auth.lockout.duration` | int | `900` | 60-86400 | Lockout duration (seconds) |
| `auth.oauth.google` | bool | `true` | — | Enable Google OAuth |
| `auth.oauth.apple` | bool | `true` | — | Enable Apple OAuth |
| `auth.oauth.state_ttl` | int | `600` | 60-3600 | OAuth state parameter TTL |

### Chat

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `chat.messages.max_length` | int | `5000` | Max message character length |
| `chat.messages.edit_window_minutes` | int | `15` | Minutes after send that editing is allowed |
| `chat.messages.preview_length` | int | `200` | Truncation length for previews |
| `chat.groups.max_participants` | int | `100` | Max participants per group conversation |
| `chat.requests.enabled` | bool | `true` | Enable chat request feature |
| `chat.requests.max_messages` | int | `3` | Messages allowed before request accepted |
| `chat.requests.expiry_days` | int | `30` | Days before stale requests are cleaned |
| `chat.attachments.max_per_message` | int | `10` | Attachments per message |
| `chat.attachments.max_image_size_mb` | int | `10` | Max image upload size (MB) |
| `chat.attachments.allowed_image_types` | array | `["jpeg","png","gif","webp"]` | Allowed image MIME subtypes |
| `chat.rate_limits.messages_per_minute` | int | `30` | Message send rate limit |
| `chat.rate_limits.conversations_per_hour` | int | `5` | Conversation creation rate limit |
| `chat.rate_limits.requests_per_hour` | int | `10` | Chat request rate limit |
| `chat.presence.ttl_seconds` | int | `30` | Presence indicator TTL |
| `chat.presence.heartbeat_interval_seconds` | int | `20` | WebSocket heartbeat interval |

### CMS

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `cms.max_versions_per_placement` | int | `50` | Max content versions kept per placement |
| `cms.max_folder_depth` | int | `5` | Maximum folder nesting depth |
| `cms.version_throttle_seconds` | int | `30` | Minimum seconds between version creates |
| `cms.api_key_rate_limit` | int | `60` | API key requests per minute |
| `cms.allowed_media_types` | array | `[10 types]` | Allowed media upload MIME subtypes |

### Other

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `transaction.default_expiry_days` | int | `30` | Default transaction expiration |
| `transaction.resubmission_cooldown_days` | int | `7` | Days before resubmission allowed |
| `transaction.expiration_reminder_hours` | int | `48` | Hours before expiry to send reminder |
| `network.follow_approval_required` | bool | `false` | Override: require approval for all follows (even public businesses) |
| `network.connection_approval_required` | bool | `true` | Require approval for connections |
| `notifications.log_retention_days` | int | `90` | Notification log retention |
| `notifications.email_enabled` | bool | `true` | Enable email notifications (deployment-wide) |
| `notifications.push_enabled` | bool | `true` | Enable push notifications |
| `notifications.sms_enabled` | bool | `true` | Enable SMS notifications |
| `explore.results_per_page` | int | `20` | Search results per page |
| `explore.min_search_length` | int | `2` | Minimum query length (shorter → empty results) |
| `explore.suggested_tags_enabled` | bool | `true` | Enable tag suggestions endpoint |
| `infra.audit_log_retention_days` | int | `730` | Audit log retention (2 years) |
| `infra.email_log_retention_days` | int | `90` | Email delivery log retention |

---

## 8. Deployment Profiles

### Minimal (User-Only)

Social network with user profiles, explore, chat, and network — no business or platform features.

```json
{
  "org_mode": "user_only",
  "systems": {
    "transaction": false,
    "forms": false,
    "network": true,
    "chat": true,
    "cms": false,
    "explore": true
  },
  "limits": {
    "max_users": 0,
    "max_businesses": 0,
    "max_businesses_per_user": 0
  },
  "user": {
    "can_create_business": false,
    "can_be_member": false,
    "profile_visibility": true,
    "profile_default_public": true,
    "max_memberships": 0,
    "forms": false,
    "network": {
      "enabled": true,
      "connections": true,
      "follows": true,
      "max_connections": 0,
      "max_follows": 0
    },
    "chat": {
      "enabled": true,
      "group": true,
      "file_sharing": true,
      "reactions": true,
      "search": true,
      "max_groups": 0
    },
    "explore": {
      "can_explore": true,
      "search_users": true,
      "search_businesses": false,
      "is_discoverable": true
    },
    "transactions": {
      "enabled": false,
      "max_pending": 0
    }
  },
  "business": {},
  "platform": {},
  "chat": {
    "messages": {"max_length": 5000, "edit_window_minutes": 15, "preview_length": 200},
    "groups": {"max_participants": 50},
    "requests": {"enabled": true, "max_messages": 3, "expiry_days": 30},
    "attachments": {"max_per_message": 5, "max_image_size_mb": 5, "allowed_image_types": ["jpeg", "png", "gif", "webp"]},
    "rate_limits": {"messages_per_minute": 20, "conversations_per_hour": 5, "requests_per_hour": 10},
    "presence": {"ttl_seconds": 30, "heartbeat_interval_seconds": 20},
    "reactions": {"types": ["like", "heart", "laugh", "wow", "sad", "angry"]}
  },
  "network": {"follow_approval_required": false, "connection_approval_required": true},
  "auth": {
    "signup": {"email_password": true, "email_verification_required": true},
    "verification": {"method": "both", "code_length": 6, "expiry_minutes": 15},
    "password_reset": {"method": "link", "expiry_minutes": 60},
    "sessions": {"max_per_user": 5, "access_token_lifetime": 900, "refresh_token_lifetime": 604800},
    "lockout": {"max_failed_attempts": 10, "duration": 900},
    "oauth": {"google": true, "apple": true, "state_ttl": 600}
  },
  "notifications": {"log_retention_days": 90, "email_enabled": true, "push_enabled": true, "sms_enabled": false},
  "explore": {"results_per_page": 20, "min_search_length": 2, "suggested_tags_enabled": true},
  "infra": {"audit_log_retention_days": 365, "email_log_retention_days": 90}
}
```

### Community (User + Platform)

Forum/community with platform management — users can join the platform, explore, chat, but no business accounts.

```json
{
  "org_mode": "user_and_platform",
  "systems": {
    "transaction": true,
    "forms": true,
    "network": true,
    "chat": true,
    "cms": true,
    "explore": true
  },
  "limits": {
    "max_users": 0,
    "max_businesses": 0,
    "max_businesses_per_user": 0
  },
  "user": {
    "can_create_business": false,
    "can_be_member": true,
    "profile_visibility": true,
    "profile_default_public": true,
    "max_memberships": 5,
    "forms": true,
    "network": {
      "enabled": true,
      "connections": true,
      "follows": true,
      "max_connections": 500,
      "max_follows": 1000
    },
    "chat": {
      "enabled": true,
      "group": true,
      "file_sharing": true,
      "reactions": true,
      "search": true,
      "max_groups": 50
    },
    "explore": {
      "can_explore": true,
      "search_users": true,
      "search_businesses": false,
      "is_discoverable": true
    },
    "transactions": {
      "enabled": true,
      "max_pending": 10
    }
  },
  "business": {},
  "platform": {
    "members": {
      "enabled": true,
      "invitations": true,
      "requests": true,
      "custom_roles": true,
      "max_members": 0,
      "max_roles": 20
    },
    "chat": {"enabled": true, "entity": true},
    "network": true,
    "forms": true,
    "cms": true,
    "governance": {
      "business_approval": false,
      "business_verification": false,
      "approved_creators": false,
      "global_moderation": true
    },
    "transactions": {"ownership_transfer": true}
  },
  "chat": {
    "messages": {"max_length": 5000, "edit_window_minutes": 15, "preview_length": 200},
    "groups": {"max_participants": 100},
    "requests": {"enabled": true, "max_messages": 3, "expiry_days": 30},
    "attachments": {"max_per_message": 10, "max_image_size_mb": 10, "allowed_image_types": ["jpeg", "png", "gif", "webp"]},
    "rate_limits": {"messages_per_minute": 30, "conversations_per_hour": 5, "requests_per_hour": 10},
    "presence": {"ttl_seconds": 30, "heartbeat_interval_seconds": 20},
    "reactions": {"types": ["like", "heart", "laugh", "wow", "sad", "angry"]}
  },
  "cms": {
    "max_versions_per_placement": 50,
    "max_folder_depth": 5,
    "version_throttle_seconds": 30,
    "api_key_rate_limit": 60,
    "allowed_media_types": ["jpeg", "png", "gif", "webp", "svg", "pdf", "mp4", "webm", "mp3", "ogg"]
  },
  "transaction": {"default_expiry_days": 30, "resubmission_cooldown_days": 7, "expiration_reminder_hours": 48},
  "network": {"follow_approval_required": false, "connection_approval_required": true},
  "auth": {
    "signup": {"email_password": true, "email_verification_required": true},
    "verification": {"method": "both", "code_length": 6, "expiry_minutes": 15},
    "password_reset": {"method": "link", "expiry_minutes": 60},
    "sessions": {"max_per_user": 5, "access_token_lifetime": 900, "refresh_token_lifetime": 604800},
    "lockout": {"max_failed_attempts": 10, "duration": 900},
    "oauth": {"google": true, "apple": true, "state_ttl": 600}
  },
  "notifications": {"log_retention_days": 90, "email_enabled": true, "push_enabled": true, "sms_enabled": true},
  "explore": {"results_per_page": 20, "min_search_length": 2, "suggested_tags_enabled": true},
  "infra": {"audit_log_retention_days": 730, "email_log_retention_days": 90}
}
```

### Full (SaaS)

All features enabled — this is the default development configuration (`deployment_config.json` in repo):

```json
{
  "org_mode": "full",
  "systems": {
    "transaction": true, "forms": true, "network": true,
    "chat": true, "cms": true, "explore": true
  }
}
```

See `backend/deployment_config.json` for the complete full config with all fields explicitly set.

---

## 9. Runtime Changes

| Change Type | Requires Restart? | How |
|------------|-------------------|-----|
| **System toggles** (`systems.*`) | **Yes** | URLs are fixed at startup. Must restart the Django process. |
| **Org mode** (`org_mode`) | **Yes** | Affects URL registration (business/platform routes). |
| **Feature gates** (FG) | No | Modify JSON, call `feature_config.reload()` or restart. |
| **Limits** (VG) | No | Modify JSON, call `feature_config.reload()` or restart. |
| **Config values** (VG) | No | Modify JSON, call `feature_config.reload()` or restart. |

### Reloading Config

```python
from apps.core.feature_config import feature_config
feature_config.reload()
```

This re-reads the JSON file. FG and VG changes take effect immediately. SG changes (system toggles, org_mode) have no effect until restart because URLs are already assembled.

---

## 10. Validation Checklist

After configuring a deployment, verify:

1. **Server starts without errors**: `python manage.py runserver` should show no import errors
2. **Health check responds**: `GET /health/` returns 200
3. **Expected URLs resolve**: Enabled systems should return 200/401 (not 404)
4. **Disabled URLs return 404**: Systems in `systems.*: false` should 404
5. **Auth works**: `POST /api/v1/auth/login/` returns tokens
6. **Feature gates respond correctly**: Disabled features should return 403 with `feature_disabled` code
7. **Limits enforce**: Try exceeding a non-zero limit — should get 400 with `business_rule_violation`

### Quick Smoke Test

```bash
# Health
curl http://localhost:8000/health/

# Auth (should always work)
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'

# Check a gated system (should 404 if off, 200/401 if on)
curl http://localhost:8000/api/v1/network/following/

# Check a gated feature (should 403 if off)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/explore/users/?q=test
```

---

## 11. Troubleshooting

### Feature returns 403 `feature_disabled` unexpectedly

**Cause**: Feature path missing from config, or set to `false`.

**Fix**: Check that the feature path exists in `deployment_config.json` and is set to `true`. Remember: `is_feature_enabled()` defaults to `false` for missing paths.

### System returns 404 but config says `true`

**Cause**: Server was started before config was updated, or config file path is wrong.

**Fix**: Verify `DEPLOYMENT_CONFIG_PATH` points to the correct file. Restart the server (SG changes require restart).

### Limit not enforcing (accepting more than limit)

**Cause**: Limit set to `0` (unlimited) in config, or the model field also has a limit that's being used instead.

**Fix**: For dual-source limits (max_members), check both config AND the model field. `effective_limit()` takes the tighter of the two.

### Tests failing with 403/FeatureDisabled after adding new feature

**Cause**: New feature path not added to `_FULL_FEATURE_CONFIG` in `backend/conftest.py`.

**Fix**: Add the path with appropriate `True`/`0` default to the test baseline config.

### Config changes not taking effect

**Cause**: Server serving cached config (FG/VG) or URLs already assembled (SG).

**Fix**: For FG/VG: call `feature_config.reload()` or restart. For SG: must restart.

---

## Reference

- **Implementation Reference**: `docs/implementations/backend/feature-gate-system.md`
- **Developer Guide**: `docs/implementations/backend/feature-gate-developer-guide.md`
- **Annotated Example**: `docs/descriptions/backend/deployment_config_full_example.json`
- **Current Dev Config**: `backend/deployment_config.json`
