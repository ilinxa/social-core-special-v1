# Deployment Configuration Form — Source of Truth

> **Purpose:** Complete this form for each client deployment.
> Every field has a default value. Only override what the client needs.
> Dependencies are enforced: child features auto-disable when parent is OFF.
> **129 configurable fields** across 15 sections.

---

## Section 1: Deployment Identity

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `deployment.name` | text | YES | — | Client/company name (e.g., "Acme Corp") |
| `deployment.code` | slug | YES | — | Unique deployment ID (e.g., "acme-corp") |
| `deployment.environment` | select | YES | `production` | Options: `production`, `staging`, `demo` |
| `deployment.region` | select | YES | — | Options: `us-east`, `eu-west`, `ap-south`, etc. |
| `deployment.tier` | select | YES | `standard` | Options: `starter`, `standard`, `professional`, `enterprise` |
| `deployment.created_at` | date | auto | — | Deployment creation date |
| `deployment.licensed_until` | date | YES | — | License expiration date |
| `deployment.notes` | textarea | NO | — | Internal notes about this client |

---

## Section 2: Organization Mode

| Field | Type | Default | Options | Description |
|-------|------|---------|---------|-------------|
| `org.mode` | select | `full` | `user_only`, `user_and_platform`, `full` | Which account layers are active |

**What each mode means:**

| Mode | Users | Platform | Businesses | Use case |
|------|-------|----------|------------|----------|
| `user_only` | YES | NO | NO | Simple social app, no org structure |
| `user_and_platform` | YES | YES | NO | Platform with users, no business accounts |
| `full` | YES | YES | YES | Full multi-tenant with businesses |

---

## Section 3: System Gates

> These control entire backend systems. When OFF, URLs return 404, tasks don't run, handlers don't register.

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `system.transaction` | boolean | ON | `org.mode != user_only` | Invitation/request/approval state machine |
| `system.forms` | boolean | ON | — | Dynamic form builder and responses |
| `system.network` | boolean | ON | — | Follow and connection system |
| `system.chat` | boolean | OFF | — | Real-time messaging (DM + group) |
| `system.cms` | boolean | ON | — | Content management system |
| `system.explore` | boolean | ON | — | Search and discovery |

**System dependency enforcement:**
- If `org.mode = user_only` → `system.transaction` forced OFF
- If `system.transaction = OFF` → invitations, requests, approvals all unavailable
- If `system.network = OFF` → chat requests always required (no connection check)

---

## Section 4: Deployment-Wide Limits

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `limits.max_users` | integer | 0 | 0 | — | users | Max registered users (0 = unlimited) |
| `limits.max_businesses` | integer | 0 | 0 | — | accounts | Max business accounts (0 = unlimited) |
| `limits.max_businesses_per_user` | integer | 1 | 1 | 100 | accounts | Max businesses one user can own |

> Depends on: `limits.max_businesses` requires `org.mode = full`

---

## Section 5: User Features

### 5.1 User — Network

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `user.network` | boolean | ON | `system.network` | User can use follow/connection system |
| `user.network.connections` | boolean | ON | `user.network` | User-to-User connections |
| `user.network.follows` | boolean | ON | `user.network` | User-to-Business/Platform follows |
| `user.limits.max_connections` | integer | 0 | `user.network.connections` | Max user connections (0 = unlimited) |
| `user.limits.max_follows` | integer | 0 | `user.network.follows` | Max follows (0 = unlimited) |

### 5.2 User — Chat

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `user.chat` | boolean | ON | `system.chat` | User can use chat system |
| `user.chat.group` | boolean | ON | `user.chat` | User can create/join group chats |
| `user.chat.file_sharing` | boolean | ON | `user.chat` | User can send image attachments |
| `user.chat.reactions` | boolean | ON | `user.chat` | User can react to messages |
| `user.chat.search` | boolean | ON | `user.chat` | User can search message history |
| `user.limits.max_chat_groups` | integer | 0 | `user.chat.group` | Max groups user can create (0 = unlimited) |

### 5.3 User — Explore & Discovery

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `user.explore` | boolean | ON | `system.explore` | User can use search/discovery |
| `user.explore.users` | boolean | ON | `user.explore` | Can search for other users |
| `user.explore.businesses` | boolean | ON | `user.explore` + `org.mode = full` | Can search for businesses |

### 5.4 User — Organization Participation

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `user.can_create_business` | boolean | FALSE | `org.mode = full` | Users can request business creation |
| `user.can_be_member` | boolean | ON | `org.mode != user_only` | Users can join businesses/platform |
| `user.limits.max_memberships` | integer | 0 | `user.can_be_member` | Max business/platform memberships (0 = unlimited) |

### 5.5 User — Transactions & Forms

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `user.transactions` | boolean | ON | `system.transaction` | User can send/receive transactions |
| `user.limits.max_pending_transactions` | integer | 0 | `user.transactions` | Max pending sent transactions (0 = unlimited) |
| `user.forms` | boolean | ON | `system.forms` | User can fill and submit forms |

### 5.6 User — Profile & Visibility

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `user.profile_visibility` | boolean | ON | — | User can control profile field visibility |
| `user.profile_default_public` | boolean | TRUE | — | New profiles default to public |

---

## Section 6: Business Features

> All fields in this section require `org.mode = full`

### 6.1 Business — Members

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.members` | boolean | ON | — | Businesses can have members |
| `business.members.invitations` | boolean | ON | `business.members` + `system.transaction` | Can send membership invitations |
| `business.members.requests` | boolean | ON | `business.members` + `system.transaction` | Can receive join requests |
| `business.members.custom_roles` | boolean | ON | `business.members` | Can create custom RBAC roles |
| `business.limits.max_members` | integer | 1 | `business.members` | Default max members per business (0 = unlimited) |
| `business.limits.max_roles` | integer | 0 | `business.members.custom_roles` | Max custom roles per business (0 = unlimited) |

### 6.2 Business — Permissions Control

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.permissions.available` | multiselect | ALL | `business.members.custom_roles` | Which RBAC permissions businesses can assign to roles |

**Available permission choices (17 business-scoped):**

| Permission | Category | Description |
|------------|----------|-------------|
| `can_invite_member` | membership | Invite new members |
| `can_remove_member` | membership | Remove members |
| `can_change_member_role` | membership | Change member roles |
| `can_suspend_member` | membership | Suspend member access |
| `can_ban_member` | membership | Ban members permanently |
| `can_approve_membership_request` | membership | Approve join requests |
| `can_view_members` | membership | View members list |
| `can_create_role` | roles | Create custom roles |
| `can_edit_role` | roles | Edit existing roles |
| `can_delete_role` | roles | Delete custom roles |
| `can_edit_business` | settings | Edit business settings |
| `can_edit_profile` | settings | Edit public profile |
| `can_view_settings` | settings | View account settings |
| `can_view_legal_info` | visibility | View registration/tax info |
| `can_view_transactions` | transactions | View account transactions |
| `can_configure_transactions` | transactions | Configure form-transaction mapping |
| `can_manage_chat` | chat | Manage business entity chat |

### 6.3 Business — Chat

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.chat` | boolean | ON | `system.chat` | Business-scope internal chat |
| `business.chat.entity` | boolean | ON | `system.chat` | Business can chat as an entity (global scope) |
| `business.chat.group` | boolean | ON | `business.chat` | Group chats within business |
| `business.chat.file_sharing` | boolean | ON | `business.chat` | File sharing in business chat |
| `business.limits.max_chat_groups` | integer | 0 | `business.chat.group` | Max groups per business (0 = unlimited) |

### 6.4 Business — Network

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.network` | boolean | ON | `system.network` | Business participates in network |
| `business.network.followers` | boolean | ON | `business.network` | Users can follow this business |
| `business.network.connections` | boolean | ON | `business.network` | Business-to-Business/Platform connections |
| `business.limits.max_followers` | integer | 0 | `business.network.followers` | Max followers (0 = unlimited) |
| `business.limits.max_connections` | integer | 0 | `business.network.connections` | Max account connections (0 = unlimited) |

### 6.5 Business — Forms

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.forms` | boolean | ON | `system.forms` | Business can create custom forms |
| `business.forms.transaction_mapping` | boolean | ON | `business.forms` + `system.transaction` | Can require forms for transactions |
| `business.limits.max_forms` | integer | 0 | `business.forms` | Max form templates per business (0 = unlimited) |

### 6.6 Business — CMS

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.cms` | boolean | ON | `system.cms` | Business has CMS content management |

### 6.7 Business — Explore & Visibility

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.explore_listing` | boolean | ON | `system.explore` | Business appears in search results |
| `business.profile_visibility` | boolean | ON | — | Business can control field visibility |
| `business.profile_default_public` | boolean | TRUE | — | New business profiles default to public |

### 6.8 Business — Transactions

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `business.transactions` | boolean | ON | `system.transaction` | Business-level transactions |
| `business.transactions.verification` | boolean | ON | `business.transactions` | Business verification workflow |
| `business.transactions.ownership_transfer` | boolean | ON | `business.transactions` | Ownership transfer capability |

---

## Section 7: Platform Features

> All fields in this section require `org.mode != user_only`

### 7.1 Platform — Members

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `platform.members` | boolean | ON | — | Platform can have members |
| `platform.members.invitations` | boolean | ON | `platform.members` + `system.transaction` | Can send membership invitations |
| `platform.members.requests` | boolean | ON | `platform.members` + `system.transaction` | Can receive join requests |
| `platform.members.custom_roles` | boolean | ON | `platform.members` | Can create custom platform roles |
| `platform.limits.max_members` | integer | 5 | `platform.members` | Max platform members (0 = unlimited) |
| `platform.limits.max_roles` | integer | 0 | `platform.members.custom_roles` | Max custom roles (0 = unlimited) |

### 7.2 Platform — Chat

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `platform.chat` | boolean | ON | `system.chat` | Platform-scope internal chat |
| `platform.chat.entity` | boolean | ON | `system.chat` | Platform can chat as entity (global scope) |

### 7.3 Platform — Network, Forms, CMS

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `platform.network` | boolean | ON | `system.network` | Platform participates in network |
| `platform.forms` | boolean | ON | `system.forms` | Platform can manage forms |
| `platform.cms` | boolean | ON | `system.cms` | Platform has CMS |

### 7.4 Platform — Governance

| Field | Type | Default | Depends on | Description |
|-------|------|---------|------------|-------------|
| `platform.business_approval` | boolean | ON | `org.mode = full` | Business creation requires approval |
| `platform.business_verification` | boolean | ON | `org.mode = full` | Business verification workflow |
| `platform.approved_creators` | boolean | ON | `org.mode = full` | Approved business creators list |
| `platform.global_moderation` | boolean | ON | — | Cross-account moderation powers |
| `platform.transactions.ownership_transfer` | boolean | ON | `system.transaction` | Platform ownership transfer |

---

## Section 8: Chat Configuration

> All fields require `system.chat = ON`

### 8.1 Message Settings

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `chat.config.max_message_length` | integer | 5000 | 100 | 50000 | chars | Maximum characters per message |
| `chat.config.edit_window_minutes` | integer | 15 | 0 | 1440 | minutes | How long after sending a user can edit (0 = no editing) |
| `chat.config.message_preview_length` | integer | 200 | 50 | 500 | chars | Preview length in conversation list |

### 8.2 Group Settings

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `chat.config.max_group_participants` | integer | 100 | 3 | 1000 | users | Max participants per group chat |

### 8.3 Chat Request Settings

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `chat.config.request_enabled` | boolean | ON | — | — | — | Enable first-message gating for non-connected users |
| `chat.config.request_max_messages` | integer | 3 | 1 | 10 | messages | Messages allowed before request accepted |
| `chat.config.request_expiry_days` | integer | 30 | 1 | 365 | days | Days before pending request auto-expires |

### 8.4 Attachment Settings

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `chat.config.max_attachments_per_message` | integer | 10 | 1 | 20 | files | Max images per message |
| `chat.config.max_image_size_mb` | integer | 10 | 1 | 50 | MB | Max file size per image |
| `chat.config.allowed_image_types` | multiselect | ALL | — | — | — | Allowed: jpeg, png, gif, webp |

### 8.5 Rate Limits

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `chat.config.rate_messages_per_minute` | integer | 30 | 5 | 120 | msg/min | Message send rate limit per conversation |
| `chat.config.rate_conversations_per_hour` | integer | 5 | 1 | 50 | conv/hr | New conversation creation rate limit |
| `chat.config.rate_requests_per_hour` | integer | 10 | 1 | 50 | req/hr | Chat request rate limit |

### 8.6 Presence & WebSocket

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `chat.config.presence_ttl_seconds` | integer | 30 | 10 | 120 | seconds | Online presence heartbeat TTL |
| `chat.config.heartbeat_interval_seconds` | integer | 20 | 5 | 60 | seconds | WebSocket heartbeat interval |

### 8.7 Reaction Types

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `chat.config.reaction_types` | multiselect | ALL | Available: like, heart, laugh, wow, sad, angry |

---

## Section 9: CMS Configuration

> All fields require `system.cms = ON`

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `cms.config.max_versions_per_placement` | integer | 50 | 5 | 500 | versions | Max content version history |
| `cms.config.max_folder_depth` | integer | 5 | 2 | 10 | levels | Media folder nesting depth |
| `cms.config.version_throttle_seconds` | integer | 30 | 0 | 300 | seconds | Min time between version saves |
| `cms.config.api_key_rate_limit` | integer | 60 | 10 | 600 | req/min | Public API rate limit per key |
| `cms.config.allowed_media_types` | multiselect | ALL | — | — | — | jpeg, png, gif, webp, svg, pdf, mp4, webm, mp3, ogg |

---

## Section 10: Transaction Configuration

> All fields require `system.transaction = ON`

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `transaction.config.default_expiry_days` | integer | 30 | 1 | 365 | days | Default transaction expiration |
| `transaction.config.resubmission_cooldown_days` | integer | 7 | 0 | 90 | days | Cooldown before resubmitting denied request |
| `transaction.config.expiration_reminder_hours` | integer | 48 | 0 | 168 | hours | Send reminder X hours before expiry (0 = no reminder) |

---

## Section 11: Network Configuration

> All fields require `system.network = ON`

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `network.config.follow_approval_required` | boolean | OFF | — | — | — | Business follows require approval (uses approval request txn type) |
| `network.config.connection_approval_required` | boolean | ON | — | — | — | User connections require target acceptance |

---

## Section 12: Auth & Security Configuration

> These are always available regardless of system gates.

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `auth.config.max_sessions_per_user` | integer | 5 | 1 | 50 | sessions | Concurrent device sessions |
| `auth.config.access_token_lifetime` | integer | 900 | 60 | 86400 | seconds | JWT access token TTL |
| `auth.config.refresh_token_lifetime` | integer | 604800 | 3600 | 2592000 | seconds | Refresh token TTL (max 30 days) |
| `auth.config.max_failed_attempts` | integer | 10 | 3 | 50 | attempts | Before account lockout |
| `auth.config.lockout_duration` | integer | 900 | 60 | 86400 | seconds | Account lockout period |
| `auth.config.email_verification_required` | boolean | ON | — | — | — | Require email verification for login |
| `auth.config.oauth_google` | boolean | ON | — | — | — | Google OAuth login |
| `auth.config.oauth_apple` | boolean | ON | — | — | — | Apple OAuth login |

---

## Section 13: Notification Configuration

> Notifications system is always ON. These control behavior.

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `notifications.config.log_retention_days` | integer | 90 | 7 | 365 | days | How long to keep notification logs |
| `notifications.config.email_enabled` | boolean | ON | — | — | — | Email notification channel |
| `notifications.config.push_enabled` | boolean | OFF | — | — | — | Push notification channel |
| `notifications.config.sms_enabled` | boolean | OFF | — | — | — | SMS notification channel |

---

## Section 14: Explore Configuration

> Requires `system.explore = ON`

| Field | Type | Default | Min | Max | Unit | Description |
|-------|------|---------|-----|-----|------|-------------|
| `explore.config.results_per_page` | integer | 20 | 5 | 100 | results | Search results page size |
| `explore.config.min_search_length` | integer | 2 | 1 | 5 | chars | Minimum query length |
| `explore.config.suggested_tags_enabled` | boolean | ON | — | — | — | Show tag suggestions |

---

## Section 15: Infrastructure

> These affect deployment infrastructure, not business logic.

| Field | Type | Default | Options | Description |
|-------|------|---------|---------|-------------|
| `infra.email_backend` | select | `console` | `console`, `smtp`, `ses` | Email sending service |
| `infra.storage_backend` | select | `local` | `local`, `s3`, `r2` | File storage backend |
| `infra.sentry_enabled` | boolean | OFF | — | Error tracking via Sentry |
| `infra.admin_url_path` | text | `management-console` | — | Django admin URL path (security) |
| `infra.audit_log_retention_days` | integer | 730 | 30-3650 | Audit log retention period |
| `infra.email_log_retention_days` | integer | 90 | 7-365 | Email log retention period |

---

## Validation Rules

### Dependency Chains (auto-disable children when parent OFF)

```
org.mode = user_only
  +-- FORCE OFF: system.transaction, all business.*, all platform.*
       +-- FORCE OFF: *.invitations, *.requests (need transaction)

org.mode = user_and_platform
  +-- FORCE OFF: all business.*

system.chat = OFF
  +-- FORCE OFF: user.chat.*, business.chat.*, platform.chat.*

system.network = OFF
  +-- FORCE OFF: user.network.*, business.network.*, platform.network.*

system.forms = OFF
  +-- FORCE OFF: user.forms, business.forms.*, platform.forms

system.cms = OFF
  +-- FORCE OFF: business.cms, platform.cms

system.explore = OFF
  +-- FORCE OFF: user.explore.*, business.explore_listing

system.transaction = OFF
  +-- FORCE OFF: *.invitations, *.requests, *.ownership_transfer,
                 business.transactions.*, business.forms.transaction_mapping
```

### Numeric Constraints

- All `max_*` fields: 0 means unlimited, negative values invalid
- `limits.max_businesses_per_user` must be >= 1 if businesses enabled
- `business.limits.max_members` minimum 1 (owner counts)
- `chat.config.max_group_participants` minimum 3 (otherwise it's a DM)
- `auth.config.refresh_token_lifetime` must be > `auth.config.access_token_lifetime`

---

## Field Count Summary

| Section | Fields |
|---------|--------|
| 1. Deployment Identity | 8 |
| 2. Organization Mode | 1 |
| 3. System Gates | 6 |
| 4. Deployment-Wide Limits | 3 |
| 5. User Features | 20 |
| 6. Business Features | 29 |
| 7. Platform Features | 15 |
| 8. Chat Configuration | 16 |
| 9. CMS Configuration | 5 |
| 10. Transaction Configuration | 3 |
| 11. Network Configuration | 2 |
| 12. Auth & Security | 8 |
| 13. Notification Configuration | 4 |
| 14. Explore Configuration | 3 |
| 15. Infrastructure | 6 |
| **TOTAL** | **~129 fields** |
