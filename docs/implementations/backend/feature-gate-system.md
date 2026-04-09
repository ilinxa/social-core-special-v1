# Feature Gate System — Implementation Reference

> **Status**: Complete (6 phases, 220 tests, BUG-010 fixed)
> **Date**: 2026-03-22
> **Plan**: `docs/plans/backend/feature_gate_system/feature_gate_implementation_plan.md`

---

## 1. Overview

The Feature Gate System enables **white-label SaaS deployment** — the same codebase serves minimal (user-only), community (user + platform), and full (business + platform) deployments without code changes.

A single JSON configuration file (`deployment_config.json`) controls which systems, features, limits, and config values are active. The system enforces these gates at three levels:

| Level | Name | What it Controls | When OFF | HTTP Code | Enforcement Layer |
|-------|------|-----------------|----------|-----------|-------------------|
| **SG** | System Gate | Entire systems (URL registration) | URL never registered → natural 404 | 404 | URL routing at startup |
| **FG** | Feature Gate | Module/sub-feature access | Explicit 403 with `feature_disabled` code | 403 | DRF permission / service layer |
| **VG** | Value Gate | Numeric limits, config values | 400 with `business_rule_violation` code | 400 | Service layer |

### Enforcement Point Summary

| Gate Type | Count | Primary Locations |
|-----------|-------|-------------------|
| SG (System Gates) | ~11 | `apps.py` (5), `routing.py` (1), `outcome_handlers.py` (1), `tasks.py` (4) |
| FG (Module Gates) | ~19 | Views across 7 files |
| FG (Sub-Feature Gates) | ~22 | Services (10), Views (6), Selectors (2) |
| VG (Limits) | ~16 | Services across 8 files |
| VG (Config Values) | ~30 | Auth (10), Chat (12), CMS (2), Explore (1), Network (1), Notifications (3), Transaction (1) |
| **Total** | **~98** | |

---

## 2. Architecture

### Design Principles

1. **Minimal-by-default**: Missing config file → all systems OFF, `org_mode=user_only`. The config file is an explicit contract — if you don't provide it, you get the most restrictive deployment.
2. **Config overrides model**: Config is the ceiling. Config OFF → 403 (feature unavailable in this deployment). Model OFF → 400 (business rule, e.g., member requests closed). Different HTTP codes, different UX.
3. **SG = URL exclusion**: Disabled systems never have their URLs registered. Django returns natural 404 — no middleware overhead, no feature-check per request.
4. **FG = permission or service check**: Module-level gates use DRF permission classes. Sub-feature gates use service-layer checks.
5. **VG = limit enforcement**: Numeric limits use `check_limit()`. Config values replace hardcoded constants via `get_value()`.
6. **Dual-source limits**: When both config AND a model field define a limit (e.g., `max_members`), `effective_limit()` returns the tighter of the two (0 = unlimited in either).

### Configuration Flow

```
deployment_config.json
        │
        ▼
  FeatureConfig (singleton)
   ├── _ensure_loaded() → lazy init from DEPLOYMENT_CONFIG_PATH
   ├── get("dotted.key") → nested dict traversal
   │
   ├── SG: is_system_enabled("chat") → bool (default False)
   ├── SG: get_org_mode() → str (default "user_only")
   ├── SG: has_business() / has_platform() → bool
   │
   ├── FG: is_feature_enabled("path") → bool (default False)
   │
   ├── VG: get_limit("path") → int (default 0 = unlimited)
   ├── VG: get_value("path", default) → Any
   ├── VG: check_limit("path", current, rule=, resource=) → None or raise
   └── VG: effective_limit(config_limit, model_limit) → int
```

---

## 3. Core Module

**File**: `apps/core/feature_config.py` (170 lines)

### FeatureConfig Class

```python
class FeatureConfig:
    """Singleton deployment feature configuration.
    Lazy-loaded from a JSON config file."""

    # Internal state
    _config: dict      # Loaded JSON data
    _loaded: bool      # Whether config has been loaded

    # Access methods
    def get(dotted_key, default=None) -> Any
    def _ensure_loaded() -> None

    # SG: System Gates
    def is_system_enabled(name: str) -> bool          # default: False
    def get_org_mode() -> str                          # default: "user_only"
    def has_business() -> bool                         # org_mode == "full"
    def has_platform() -> bool                         # org_mode in {"full", "user_and_platform"}

    # FG: Feature Gates
    def is_feature_enabled(path: str) -> bool          # default: False

    # VG: Value Gates
    def get_limit(path: str, default: int = 0) -> int  # 0 = unlimited
    def get_value(path: str, default=None) -> Any
    def check_limit(path, current, *, rule, resource="") -> None  # raises BusinessRuleViolation
    @staticmethod
    def effective_limit(config_limit, model_limit) -> int  # tighter of two

    # Management
    def reload() -> None                               # FG/VG only, NOT SG
```

### Key Implementation Details

**Lazy loading** (`_ensure_loaded`): Config is loaded on first access from the path specified by `settings.DEPLOYMENT_CONFIG_PATH`. Missing file or invalid JSON → empty dict (minimal defaults).

**Dot-notation traversal** (`get`): `feature_config.get("business.members.enabled")` traverses `config["business"]["members"]["enabled"]`. Missing key at any level → returns `default`.

**`check_limit` helper**: One-liner for VG limit enforcement. 0 = unlimited (no check). Non-zero → `current >= limit` → raises `BusinessRuleViolation(rule=rule, limit=limit, current=current)`.

**`effective_limit` static method**: Resolves dual-source limits. Used when both config (`deployment_config.json`) and model field (`BusinessAccount.max_members`) define a cap:

```python
@staticmethod
def effective_limit(config_limit: int, model_limit: int) -> int:
    if config_limit == 0 and model_limit == 0:
        return 0   # both unlimited
    if config_limit == 0:
        return model_limit   # config unlimited, model sets limit
    if model_limit == 0:
        return config_limit  # model unlimited, config sets limit
    return min(config_limit, model_limit)  # both set, take tighter
```

### Module Singleton

```python
# Module-level singleton — import this everywhere
feature_config = FeatureConfig()
```

Usage: `from apps.core.feature_config import feature_config`

---

## 4. Exception Classes

### FeatureDisabled

**File**: `apps/core/exceptions/domain.py` (lines 177-202)

Raised when a feature is disabled by deployment configuration. Maps to **HTTP 403** with code `feature_disabled`.

```python
class FeatureDisabled(DomainException):
    default_message = "This feature is not available"
    default_code = "feature_disabled"

    def __init__(self, message=None, feature=None):
        details = {}
        if feature:
            details["feature"] = feature
        super().__init__(message=message, code=self.default_code, details=details)
```

**Distinct from `PermissionDenied`**: `feature_disabled` means the feature is OFF for this deployment. `permission_denied` means the user lacks RBAC permissions. Frontend distinguishes these for different UX (e.g., "Feature not available" vs "You don't have access").

### BusinessRuleViolation (extended)

**File**: `apps/core/exceptions/domain.py` (lines 352-387)

Extended with `limit` and `current` parameters for VG limit enforcement. Maps to **HTTP 400**.

```python
class BusinessRuleViolation(DomainException):
    default_code = "business_rule_violation"

    def __init__(self, message=None, rule=None, limit=None, current=None):
        details = {}
        if rule:
            details["rule"] = rule
        if limit is not None:
            details["limit"] = limit
        if current is not None:
            details["current"] = current
```

### AccountLocked

**File**: `apps/core/exceptions/domain.py` (lines 472-481)

Raised during login when account is locked after too many failed attempts. Maps to **HTTP 401**.

```python
class AccountLocked(AuthenticationError):
    default_message = "Account temporarily locked due to too many failed attempts"
    default_code = "account_locked"
```

### Exception Handler Mapping

**File**: `apps/core/exceptions/handler.py` (lines 70-96)

```python
STATUS_CODE_MAP = {
    "business_rule_violation": 400,  # VG limits
    "account_locked": 401,           # Auth lockout
    "feature_disabled": 403,         # FG gates
    # ... other codes ...
}
```

---

## 5. DRF Permission Factory

**File**: `apps/core/permissions/base.py` (lines 287-328)

`FeatureRequired()` is a **factory function** that returns a permission **class** (not instance). DRF requires `permission_classes` to contain classes, which it instantiates via `[perm() for perm in permission_classes]`.

```python
def FeatureRequired(feature_path):
    """Returns a DRF permission CLASS that checks if a feature is enabled."""

    class _FeatureRequiredPermission(BasePermission):
        _feature_path = feature_path

        def has_permission(self, request, view):
            if not feature_config.is_feature_enabled(self._feature_path):
                raise FeatureDisabled(feature=self._feature_path)
            return True

    _FeatureRequiredPermission.__name__ = f"FeatureRequired_{feature_path}"
    return _FeatureRequiredPermission
```

### Usage Patterns

**Static (class-level)**:
```python
class FollowCreateView(APIView):
    permission_classes = [IsAuthenticated, FeatureRequired("user.network.enabled")]
```

**Method-level override**:
```python
class MembershipInviteView(APIView):
    def post(self, request, slug):
        self.permission_classes = [IsAuthenticated, FeatureRequired("business.members.enabled")]
        self.check_permissions(request)
        # ... continue with logic
```

**Shared constant**:
```python
_CmsGate = FeatureRequired("platform.cms")

class ContentCreateView(APIView):
    permission_classes = [IsAuthenticated, _CmsGate]
```

---

## 6. System Gates (SG) — URL Coordinator

### Architecture

**File**: `backend_core/urls/__init__.py` (89 lines)

The URL coordinator replaces the monolithic `urls.py` with a package of URL group files. At startup, it reads the feature config and only imports URL groups that are enabled. Disabled systems never have their URLs registered — Django returns natural 404.

```python
GATED_GROUPS = {
    "organization": lambda fc: fc.has_business() or fc.has_platform(),
    "transaction":  lambda fc: fc.is_system_enabled("transaction"),
    "forms":        lambda fc: fc.is_system_enabled("forms"),
    "cms":          lambda fc: fc.is_system_enabled("cms"),
    "explore":      lambda fc: fc.is_system_enabled("explore"),
    "network":      lambda fc: fc.is_system_enabled("network"),
    "chat":         lambda fc: fc.is_system_enabled("chat"),
}

def get_enabled_groups(fc=None):
    fc = fc or feature_config
    return {name for name, check in GATED_GROUPS.items() if check(fc)}
```

Assembly is conditional imports at module level:

```python
urlpatterns = list(base_patterns)
_enabled = get_enabled_groups()

if "organization" in _enabled:
    from .organization import urlpatterns as org_patterns
    urlpatterns += org_patterns
# ... same for transaction, forms, cms, explore, network, chat
```

### URL Group Files

| File | Routes | Gate Condition |
|------|--------|----------------|
| `urls/base.py` | Auth, users, email, notifications, RBAC, health, admin | **Always on** |
| `urls/organization.py` | Business, platform | `has_business()` / `has_platform()` (internal org_mode logic) |
| `urls/transaction.py` | Transaction API | `systems.transaction` |
| `urls/forms.py` | Forms API + public forms | `systems.forms` |
| `urls/cms.py` | CMS admin + public API | `systems.cms` |
| `urls/explore.py` | Explore/search endpoints | `systems.explore` |
| `urls/network.py` | Network (follow/connect) | `systems.network` |
| `urls/chat.py` | Chat REST API | `systems.chat` |
| `urls/dev.py` | Swagger, redoc, silk, media | `DEBUG=True` only |

**Note**: `urls/organization.py` is the only group file with internal logic — it checks `has_business()` and `has_platform()` separately to include business and/or platform routes based on `org_mode`.

### WebSocket Routing

**File**: `backend_core/routing.py` (15 lines)

```python
websocket_urlpatterns = []

if feature_config.is_system_enabled("chat"):
    from apps.chat.consumers import ChatConsumer
    websocket_urlpatterns = [path("ws/chat/", ChatConsumer.as_asgi())]
```

### SG Enforcement Points (11 total)

| # | File | Line | Guard |
|---|------|------|-------|
| 1 | `apps/forms/apps.py` | 15 | `is_system_enabled("forms")` — admin registration |
| 2 | `apps/cms/apps.py` | 12 | `is_system_enabled("cms")` — admin registration |
| 3 | `apps/explore/apps.py` | 12 | `is_system_enabled("explore")` — admin registration |
| 4 | `apps/network/apps.py` | 12 | `is_system_enabled("network")` — admin registration |
| 5 | `apps/chat/apps.py` | 12 | `is_system_enabled("chat")` — admin registration |
| 6 | `backend_core/routing.py` | 9 | `is_system_enabled("chat")` — WebSocket consumer |
| 7 | `apps/transaction/outcome_handlers.py` | 312 | `is_system_enabled("network")` — network handler registration |
| 8 | `apps/transaction/tasks.py` | 16 | `is_system_enabled("transaction")` — expiration task |
| 9 | `apps/transaction/tasks.py` | 44 | `is_system_enabled("transaction")` — reminder task |
| 10 | `apps/cms/tasks.py` | 24 | `is_system_enabled("cms")` — tombstone cleanup |
| 11 | `apps/chat/tasks.py` | 27 | `is_system_enabled("chat")` — request expiry |

---

## 7. Feature Gates (FG) — Module Level

Module-level gates use `FeatureRequired("path")` in `permission_classes` to block entire views/endpoints when a feature is disabled. Returns 403 with `feature_disabled` code.

### FG Module Enforcement Points (~19 total)

| # | Feature Path | File | View/Method | Scope |
|---|-------------|------|-------------|-------|
| 1 | `user.network.enabled` | `apps/network/views.py:130` | FollowCreateView | Static |
| 2 | `user.network.enabled` | `apps/network/views.py:215` | UnfollowView | Static |
| 3 | `user.network.enabled` | `apps/network/views.py:247` | FollowingListView | Static |
| 4 | `user.network.enabled` | `apps/network/views.py:289` | FollowerListView | Static |
| 5 | `user.network.enabled` | `apps/network/views.py:331` | ConnectionRequestView | Static |
| 6 | `user.network.enabled` | `apps/network/views.py:363` | ConnectionActionView | Static |
| 7 | `user.network.enabled` | `apps/network/views.py:676` | UserConnectionsView | Static |
| 8 | `business.network.enabled` | `apps/network/views.py:408` | BusinessFollowersView | Static |
| 9 | `business.network.enabled` | `apps/network/views.py:445` | BusinessFollowerActionView | Static |
| 10 | `business.network.enabled` | `apps/network/views.py:491` | BusinessConnectionsView | Static |
| 11 | `business.network.enabled` | `apps/network/views.py:536` | BusinessConnectionActionView | Static |
| 12 | `business.network.enabled` | `apps/network/views.py:630` | NetworkStatsView | Static |
| 13 | `business.network.enabled` | `apps/network/views.py:704` | BusinessNetworkStatsView | Static |
| 14 | `user.explore.can_explore` | `apps/explore/views.py:315` | ExploreUserSearchView | Static |
| 15 | `user.forms` | `apps/forms/api/views.py:114` | SystemFormTemplateView | Static |
| 16 | `platform.cms` | `apps/cms/api/views.py:61` | `_CmsGate` shared constant | Static (17 views) |
| 17 | `user.profile_visibility` | `apps/users/views.py:534` | VisibilitySettingsView | Static |
| 18 | `user.can_create_business` | `apps/users/views.py:612` | BusinessCreationEligibilityView | Static |
| 19 | `business.profile_visibility` | `apps/organization/business/views.py:881` | BusinessVisibilityView | Static |

**Additional method-level gates**: `business.members.enabled` (business views POST), `platform.members.enabled` (platform views POST), and the `_FORMS_GATE_PATHS` mixin in forms views for business/platform form scope detection.

---

## 8. Feature Gates (FG) — Sub-Feature Level

Sub-feature gates use `is_feature_enabled()` in service/selector/view code. They raise `FeatureDisabled` or return empty results (graceful skip).

### FG Sub-Feature Enforcement Points (~22 total)

| # | Feature Path | File | Method | Behavior |
|---|-------------|------|--------|----------|
| 1 | `business.chat.entity` | `apps/chat/services.py:99` | `_validate_entity_participant()` | Raise FeatureDisabled |
| 2 | `platform.chat.entity` | `apps/chat/services.py:102` | `_validate_entity_participant()` | Raise FeatureDisabled |
| 3 | `{scope}.chat.group` | `apps/chat/services.py:149` | `create_conversation()` | Raise FeatureDisabled |
| 4 | `user.chat.file_sharing` | `apps/chat/services.py:1217` | `upload_attachment()` | Raise FeatureDisabled |
| 5 | `business.chat.file_sharing` | `apps/chat/services.py:1222` | `upload_attachment()` | Raise FeatureDisabled |
| 6 | `user.chat.reactions` | `apps/chat/services.py:1380` | `add_reaction()` | Raise FeatureDisabled |
| 7 | `user.chat.search` | `apps/chat/selectors.py:479` | `search_messages()` | Raise FeatureDisabled |
| 8 | `user.network.follows` | `apps/network/services.py:46` | `create_follow()` | Raise FeatureDisabled |
| 9 | `business.network.followers` | `apps/network/services.py:50` | `create_follow()` | Raise FeatureDisabled |
| 10 | `user.network.connections` | `apps/network/services.py:278` | `create_connection_request()` | Raise FeatureDisabled |
| 11 | `business.network.connections` | `apps/network/services.py:382` | `create_business_connection_request()` | Raise FeatureDisabled |
| 12-19 | `{type}-specific` | `apps/transaction/services.py:1302,1319` | `_check_sub_feature_gates()` | Raise FeatureDisabled (8 paths via `_INVITATION_FEATURE_GATES` + `_REQUEST_FEATURE_GATES` maps) |
| 20 | `{account_type}.members.custom_roles` | `apps/rbac/services.py:945` | `create_custom_role()` | Raise FeatureDisabled |
| 21 | `business.forms.transaction_mapping` | `apps/forms/services.py:84` | `create_transaction_form_mapping()` | Early return (graceful) |
| 22 | `user.explore.is_discoverable` | `apps/explore/selectors.py:170` | `search_users()` | Filter out non-discoverable |

**Explore view gates** (graceful skip pattern):
- `user.explore.search_users` → `apps/explore/views.py:150` — returns empty user results
- `user.explore.search_businesses` → `apps/explore/views.py:289` — returns empty business results
- Combined search → `apps/explore/views.py:380` — skips disabled sections

### Transaction Feature Gate Maps

```python
# apps/transaction/services.py
_INVITATION_FEATURE_GATES = {
    "business_membership_invitation": "business.members.invitations",
    "platform_membership_invitation": "platform.members.invitations",
    "business_verification_request": "business.transactions.verification",
    "ownership_transfer_request": "business.transactions.ownership_transfer",
    "platform_ownership_transfer_request": "platform.transactions.ownership_transfer",
}

_REQUEST_FEATURE_GATES = {
    "business_membership_request": "business.members.requests",
    "platform_membership_request": "platform.members.requests",
    "business_creation_approval_request": "platform.governance.business_approval",
}
```

---

## 9. Value Gates (VG) — Limits

### VG Limit Enforcement Points (~16 total)

| # | Config Path | File | Method | Default | Rule Name |
|---|------------|------|--------|---------|-----------|
| 1 | `limits.max_users` | `apps/users/services.py:165` | `create_user()` | 0 | `user_limit_reached` |
| 2 | `limits.max_businesses` | `apps/organization/business/services.py:112` | `create_business()` | 0 | `business_limit_reached` |
| 3 | `limits.max_businesses_per_user` | `apps/organization/business/services.py:118` | `create_business()` | 0 | `business_per_user_limit_reached` |
| 4 | `user.max_memberships` | `apps/rbac/services.py:389` | `create_membership()` | 0 | `membership_limit_reached` |
| 5 | `{type}.members.max_roles` | `apps/rbac/services.py:954` | `create_custom_role()` | 0 | `role_limit_reached` |
| 6 | `user.transactions.max_pending` | `apps/transaction/services.py:138` | `create_invitation()` | 0 | `pending_transaction_limit_reached` |
| 7 | `user.transactions.max_pending` | `apps/transaction/services.py:322` | `create_request()` | 0 | `pending_transaction_limit_reached` |
| 8 | `user.network.max_follows` | `apps/network/services.py:58` | `create_follow()` | 0 | `follow_limit_reached` |
| 9 | `business.network.max_followers` | `apps/network/services.py:72` | `create_follow()` | 0 | `follower_limit_reached` |
| 10 | `user.network.max_connections` | `apps/network/services.py:288` | `create_connection_request()` | 0 | `connection_limit_reached` |
| 11 | `business.network.max_connections` | `apps/network/services.py:392` | `create_business_connection_request()` | 0 | `connection_limit_reached` |
| 12 | `user.chat.max_groups` | `apps/chat/services.py:160` | `create_conversation()` (global scope) | 0 | `group_limit_reached` |
| 13 | `business.chat.max_groups` | `apps/chat/services.py:172` | `create_conversation()` (business scope) | 0 | `group_limit_reached` |
| 14 | `business.forms.max_forms` | `apps/forms/services.py:84` | `create_form_template()` | 0 | `form_limit_reached` |

### Dual-Source Limits (effective_limit)

| Config Path | Model Field | File | Method |
|-------------|-------------|------|--------|
| `{type}.members.max_members` | `BusinessAccount.max_members` / `PlatformAccount.max_members` | `apps/rbac/services.py:370-373` | `create_membership()` |
| `{type}.members.max_members` | `BusinessAccount.max_members` / `PlatformAccount.max_members` | `apps/transaction/services.py:1108-1111` | `_check_member_quota()` |

---

## 10. Value Gates (VG) — Config Values

Config values replace hardcoded constants with deployment-configurable values via `get_value()`.

### VG Config Value Enforcement Points (~30 total)

#### Auth Service (10 points)

| # | Config Path | File:Line | Default | Replaces |
|---|------------|-----------|---------|----------|
| 1 | `auth.lockout.max_failed_attempts` | `apps/auth/services/auth_service.py:166` | 10 | Hardcoded constant |
| 2 | `auth.lockout.duration` | `apps/auth/services/auth_service.py:168` | 900 (seconds) | Hardcoded constant |
| 3 | `auth.sessions.access_token_lifetime` | `apps/auth/services/auth_service.py:426` | 900 (seconds) | `settings.ACCESS_TOKEN_LIFETIME` |
| 4 | `auth.sessions.refresh_token_lifetime` | `apps/auth/services/auth_service.py:427` | 604800 (7 days) | `settings.REFRESH_TOKEN_LIFETIME` |
| 5 | `auth.sessions.access_token_lifetime` | `apps/auth/services/auth_service.py:646` | 900 | Token refresh |
| 6 | `auth.sessions.access_token_lifetime` | `apps/auth/services/auth_service.py:683` | 900 | Token creation |
| 7 | `auth.sessions.refresh_token_lifetime` | `apps/auth/services/auth_service.py:684` | 604800 | Token creation |
| 8 | `auth.sessions.max_per_user` | `apps/auth/services/auth_service.py:717` | 5 | `settings.MAX_SESSIONS_PER_USER` |
| 9 | `auth.verification.expiry_minutes` | `apps/auth/models.py:318` | 15 | `timedelta(minutes=15)` |
| 10 | `auth.password_reset.expiry_minutes` | `apps/auth/models.py:394` | 60 | `timedelta(minutes=60)` |

#### Chat Service (12 points)

| # | Config Path | File:Line | Default | Replaces |
|---|------------|-----------|---------|----------|
| 1 | `chat.groups.max_participants` | `apps/chat/services.py:184` | 100 | `MAX_PARTICIPANTS` |
| 2 | `chat.messages.max_length` | `apps/chat/services.py:369` | 5000 | `MAX_MESSAGE_LENGTH` |
| 3 | `chat.messages.edit_window_minutes` | `apps/chat/services.py:496` | 15 | `EDIT_WINDOW_MINUTES` |
| 4 | `chat.messages.max_length` | `apps/chat/services.py:511` | 5000 | Edit validation |
| 5 | `chat.messages.preview_length` | `apps/chat/services.py:538` | 200 | Preview truncation |
| 6 | `chat.groups.max_participants` | `apps/chat/services.py:788` | 100 | Add participant |
| 7 | `chat.attachments.max_image_size_mb` | `apps/chat/services.py:1260` | 10 | Upload validation |
| 8 | `chat.attachments.max_per_message` | `apps/chat/services.py:1324` | 10 | Attachment limit |
| 9 | `chat.requests.max_messages` | `apps/chat/services.py:1599` | 3 | Request message limit |
| 10 | `chat.messages.preview_length` | `apps/chat/services.py:1624` | 200 | Request preview |
| 11 | `chat.requests.expiry_days` | `apps/chat/tasks.py:34` | 30 | Stale request cleanup |
| 12 | `chat.presence.heartbeat_interval_seconds` | `apps/chat/consumers.py:611` | 20 | WebSocket heartbeat |

#### Other Services (8 points)

| # | Config Path | File:Line | Default | Replaces |
|---|------------|-----------|---------|----------|
| 1 | `chat.presence.ttl_seconds` | `apps/chat/presence.py:58` | 30 | Presence TTL |
| 2 | `cms.version_throttle_seconds` | `apps/cms/services.py:1352` | 30 | Version creation throttle |
| 3 | `cms.max_versions_per_placement` | `apps/cms/services.py:1373` | 50 | Version cap |
| 4 | `explore.min_search_length` | `apps/explore/views.py:135` | 2 | Minimum query length |
| 5 | `network.follow_approval_required` | `apps/network/views.py:181` | False | Override is_public for follow |
| 6 | `notifications.email_enabled` | `apps/notifications/services/notification_service.py:85` | True | Channel toggle |
| 7 | `notifications.push_enabled` | `apps/notifications/services/notification_service.py:86` | True | Channel toggle |
| 8 | `notifications.sms_enabled` | `apps/notifications/services/notification_service.py:87` | True | Channel toggle |

---

## 11. Configuration Schema

### Full Config Reference (123 fields in deployment_config.json)

#### Top-Level

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `org_mode` | string | `"user_only"` | `"full"` / `"user_and_platform"` / `"user_only"` |

#### Systems (`systems.*`) — 6 booleans

| Path | Default | Controls |
|------|---------|----------|
| `systems.transaction` | `false` | Transaction API URLs, tasks, outcome handlers |
| `systems.forms` | `false` | Forms API URLs, admin registration |
| `systems.network` | `false` | Network (follow/connect) URLs, admin, outcome handlers |
| `systems.chat` | `false` | Chat REST + WebSocket URLs, admin, tasks |
| `systems.cms` | `false` | CMS admin + public API URLs, tasks |
| `systems.explore` | `false` | Explore/search URLs, admin |

#### Global Limits (`limits.*`) — 3 values

| Path | Default | Description |
|------|---------|-------------|
| `limits.max_users` | `0` | Maximum users (0 = unlimited) |
| `limits.max_businesses` | `0` | Maximum businesses (0 = unlimited) |
| `limits.max_businesses_per_user` | `0` | Max businesses per user (0 = unlimited) |

#### User Features (`user.*`) — 23 fields

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `user.can_create_business` | bool | `false` | FG: business creation eligibility view |
| `user.can_be_member` | bool | `false` | FG: membership eligibility |
| `user.profile_visibility` | bool | `false` | FG: visibility settings view |
| `user.profile_default_public` | bool | `false` | Default profile visibility |
| `user.max_memberships` | int | `0` | VG: max org memberships per user |
| `user.forms` | bool | `false` | FG: system form template access |
| `user.network.enabled` | bool | `false` | FG: all user network views |
| `user.network.connections` | bool | `false` | FG sub: user connection requests |
| `user.network.follows` | bool | `false` | FG sub: user follows |
| `user.network.max_connections` | int | `0` | VG: max user connections |
| `user.network.max_follows` | int | `0` | VG: max user follows |
| `user.chat.enabled` | bool | `false` | FG: chat participation |
| `user.chat.group` | bool | `false` | FG sub: group conversation creation |
| `user.chat.file_sharing` | bool | `false` | FG sub: attachment uploads |
| `user.chat.reactions` | bool | `false` | FG sub: message reactions |
| `user.chat.search` | bool | `false` | FG sub: message search |
| `user.chat.max_groups` | int | `0` | VG: max conversations (global scope) |
| `user.explore.can_explore` | bool | `false` | FG: user search view |
| `user.explore.search_users` | bool | `false` | FG sub: user search results |
| `user.explore.search_businesses` | bool | `false` | FG sub: business search results |
| `user.explore.is_discoverable` | bool | `false` | FG sub: appear in search results |
| `user.transactions.enabled` | bool | `false` | FG sub: transaction creation |
| `user.transactions.max_pending` | int | `0` | VG: max pending transactions |

#### Business Features (`business.*`) — 25 fields

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `business.members.enabled` | bool | `false` | FG: member invitation/request POST |
| `business.members.invitations` | bool | `false` | FG sub: membership invitations |
| `business.members.requests` | bool | `false` | FG sub: membership requests |
| `business.members.custom_roles` | bool | `false` | FG sub: custom role creation |
| `business.members.max_members` | int | `0` | VG: max members (dual-source) |
| `business.members.max_roles` | int | `0` | VG: max custom roles |
| `business.chat.enabled` | bool | `false` | FG: business chat |
| `business.chat.entity` | bool | `false` | FG sub: business as chat participant |
| `business.chat.group` | bool | `false` | FG sub: business group conversations |
| `business.chat.file_sharing` | bool | `false` | FG sub: business attachment uploads |
| `business.chat.max_groups` | int | `0` | VG: max conversations (business scope) |
| `business.network.enabled` | bool | `false` | FG: all business network views |
| `business.network.followers` | bool | `false` | FG sub: business followers management |
| `business.network.connections` | bool | `false` | FG sub: business connections |
| `business.network.max_followers` | int | `0` | VG: max business followers |
| `business.network.max_connections` | int | `0` | VG: max business connections |
| `business.forms.enabled` | bool | `false` | FG: business form views (mixin) |
| `business.forms.transaction_mapping` | bool | `false` | FG sub: form-transaction mapping |
| `business.forms.max_forms` | int | `0` | VG: max form templates |
| `business.cms` | bool | `false` | FG: business CMS (no views yet) |
| `business.profile_visibility` | bool | `false` | FG: business visibility settings view |
| `business.profile_default_public` | bool | `false` | Default business profile visibility |
| `business.transactions.enabled` | bool | `false` | FG sub: business transaction creation |
| `business.transactions.verification` | bool | `false` | FG sub: verification requests |
| `business.transactions.ownership_transfer` | bool | `false` | FG sub: ownership transfer |

#### Platform Features (`platform.*`) — 16 fields

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `platform.members.enabled` | bool | `false` | FG: platform member invitation/request |
| `platform.members.invitations` | bool | `false` | FG sub: platform membership invitations |
| `platform.members.requests` | bool | `false` | FG sub: platform membership requests |
| `platform.members.custom_roles` | bool | `false` | FG sub: platform custom role creation |
| `platform.members.max_members` | int | `0` | VG: max platform members (dual-source) |
| `platform.members.max_roles` | int | `0` | VG: max platform custom roles |
| `platform.chat.enabled` | bool | `false` | FG: platform chat |
| `platform.chat.entity` | bool | `false` | FG sub: platform as chat participant |
| `platform.network` | bool | `false` | FG: platform network |
| `platform.forms` | bool | `false` | FG: platform form views (mixin) |
| `platform.cms` | bool | `false` | FG: CMS admin views |
| `platform.governance.business_approval` | bool | `false` | FG sub: business creation approval |
| `platform.governance.business_verification` | bool | `false` | FG sub: business verification |
| `platform.governance.approved_creators` | bool | `false` | FG sub: approved creator list |
| `platform.governance.global_moderation` | bool | `false` | FG sub: global moderation |
| `platform.transactions.ownership_transfer` | bool | `false` | FG sub: platform ownership transfer |

#### Auth Config (`auth.*`) — 15 fields

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `auth.signup.email_password` | bool | `true` | Enable email+password registration |
| `auth.signup.email_verification_required` | bool | `true` | Require email verification |
| `auth.verification.method` | string | `"both"` | `"code"` / `"link"` / `"both"` |
| `auth.verification.code_length` | int | `6` | Verification code digits |
| `auth.verification.expiry_minutes` | int | `15` | Verification code/link expiry |
| `auth.password_reset.method` | string | `"link"` | Reset method |
| `auth.password_reset.expiry_minutes` | int | `60` | Reset token expiry |
| `auth.sessions.max_per_user` | int | `5` | Maximum concurrent sessions |
| `auth.sessions.access_token_lifetime` | int | `900` | Access token TTL (seconds) |
| `auth.sessions.refresh_token_lifetime` | int | `604800` | Refresh token TTL (seconds) |
| `auth.lockout.max_failed_attempts` | int | `10` | Failed logins before lockout |
| `auth.lockout.duration` | int | `900` | Lockout duration (seconds) |
| `auth.oauth.google` | bool | `true` | Google OAuth enabled |
| `auth.oauth.apple` | bool | `true` | Apple OAuth enabled |
| `auth.oauth.state_ttl` | int | `600` | OAuth state TTL (seconds) |

#### Chat Config (`chat.*`) — 15 fields

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `chat.messages.max_length` | int | `5000` | Max message character length |
| `chat.messages.edit_window_minutes` | int | `15` | Edit window after sending |
| `chat.messages.preview_length` | int | `200` | Preview truncation length |
| `chat.groups.max_participants` | int | `100` | Max participants per group |
| `chat.requests.enabled` | bool | `true` | Enable chat requests |
| `chat.requests.max_messages` | int | `3` | Messages before request accepted |
| `chat.requests.expiry_days` | int | `30` | Stale request cleanup |
| `chat.attachments.max_per_message` | int | `10` | Attachments per message |
| `chat.attachments.max_image_size_mb` | int | `10` | Max image size (MB) |
| `chat.attachments.allowed_image_types` | array | `["jpeg","png","gif","webp"]` | Allowed types |
| `chat.rate_limits.messages_per_minute` | int | `30` | Message rate limit |
| `chat.rate_limits.conversations_per_hour` | int | `5` | Conversation creation rate |
| `chat.rate_limits.requests_per_hour` | int | `10` | Chat request rate |
| `chat.presence.ttl_seconds` | int | `30` | Presence TTL |
| `chat.presence.heartbeat_interval_seconds` | int | `20` | WebSocket heartbeat |

#### CMS Config (`cms.*`) — 5 fields

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `cms.max_versions_per_placement` | int | `50` | Version cap per placement |
| `cms.max_folder_depth` | int | `5` | Folder nesting depth |
| `cms.version_throttle_seconds` | int | `30` | Min time between versions |
| `cms.api_key_rate_limit` | int | `60` | API key requests per minute |
| `cms.allowed_media_types` | array | `[10 types]` | Allowed upload types |

#### Other Config Sections

| Section | Fields | Key Paths |
|---------|--------|-----------|
| `transaction.*` | 3 | `default_expiry_days` (30), `resubmission_cooldown_days` (7), `expiration_reminder_hours` (48) |
| `network.*` | 2 | `follow_approval_required` (false), `connection_approval_required` (true) |
| `notifications.*` | 4 | `log_retention_days` (90), `email_enabled` (true), `push_enabled` (true), `sms_enabled` (true) |
| `explore.*` | 3 | `results_per_page` (20), `min_search_length` (2), `suggested_tags_enabled` (true) |
| `infra.*` | 2 | `audit_log_retention_days` (730), `email_log_retention_days` (90) |

---

## 12. Test Infrastructure

### Test Config Baseline

**File**: `backend/conftest.py` (lines 22-199)

`_FULL_FEATURE_CONFIG` is a dict mirroring `deployment_config.json` with all systems ON, all features enabled, all limits set to 0 (unlimited). This ensures the existing 4000+ tests pass unchanged.

### Setup Timing

The URL coordinator (`backend_core/urls/__init__.py`) runs assembly at import time. Test modules that import URL-related code trigger this during pytest collection — **before** session fixtures run. Solution:

1. **`pytest_configure(trylast=True)` hook** (line 202): Sets `feature_config._config` during plugin configuration, after pytest-django sets up Django but before collection starts.
2. **`_enable_all_features` session fixture** (line 219): Safety net + teardown.

### Per-Test Override Fixture

**`feature_config_override` fixture** (line 250): Returns a callable that deep-merges overrides into the current config. Restores original config after test.

```python
def test_chat_disabled(feature_config_override):
    feature_config_override({"systems": {"chat": False}})
    # chat is now off, all other features still on
```

### Test File Inventory (220 tests total)

| File | Tests | What it Covers |
|------|-------|---------------|
| `apps/core/tests/test_feature_config.py` | 76 | Foundation: config loading, dot-notation, system gates, feature gates, value gates, effective_limit, minimal deployment, FeatureDisabled exception, FeatureRequired permission, test fixtures |
| `apps/core/tests/test_url_groups.py` | 24 | SG: `get_enabled_groups()` decision logic (15), URL group file verification (9) |
| `apps/core/tests/test_sg_integration.py` | 3 | SG: URL resolution for always-on, gated, and empty config |
| `apps/core/tests/test_fg_module_gates.py` | 14 | FG Module: network (2), business (3), platform (2), forms (3), CMS (1), explore (1), users (2) |
| `apps/core/tests/test_fg_sub_feature_gates.py` | 29 | FG Sub-Feature: chat (7), network (4), transactions (4), governance (2), RBAC (2), forms (1), explore (4), member invitations/requests (4) |
| `apps/core/tests/test_vg_limits.py` | 27 | VG Limits: check_limit (2), deployment-wide (2), user (4), business (3), effective_limit (3), member quota (3), additional (7) |
| `apps/core/tests/test_vg_config_values.py` | 31 | VG Config: chat (9), CMS (2), auth (6), network (3), transaction (1), explore (2), notifications (3), behavioral bools (2), arrays (2), presence (2) |
| `tests/api_integration/test_phase_13_feature_gates.py` | 16 | Integration: account lockout (6), session limit (1), network follow (4), explore (3), notifications (2) |

---

## 13. Known Bugs Found

### BUG-010: `@transaction.atomic` Rolled Back Lockout Counter

**Discovery**: Phase 13 integration test `FG-L01` — `failed_login_attempts` stayed at 0 after failed logins.

**Root cause**: The `login()` method in `auth_service.py` was decorated with `@transaction.atomic`. When `InvalidCredentials()` was raised after incrementing `failed_login_attempts`, Django rolled back the entire atomic block — including the `user.save()` that persisted the counter.

**Fix**: Removed `@transaction.atomic` decorator. Pre-auth failure paths (lockout check, password verify, active/verified checks) now run outside any transaction. Only the success path (session creation, token generation) is wrapped in `with transaction.atomic():`.

**Impact**: All pre-auth side effects (lockout counter, audit logs) now persist even when an exception is raised. The success path remains atomic. 340 auth unit tests + 312 integration tests pass.

**Lesson**: Be careful with `@transaction.atomic` on methods that need side effects to persist on failure. Authentication methods are a common case — lockout counters, audit logs, and rate limit tracking all need to survive failed attempts.

---

## 14. Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **JSON file, not DB/Redis** | No runtime admin UI needed. Config changes are deployment events. JSON is version-controllable, diffable, and has zero dependencies. |
| 2 | **Minimal-by-default** | Security: missing config should disable features, not enable them. Prevents accidental exposure in misconfigured deployments. |
| 3 | **SG = URL exclusion at startup** | Natural 404 (no middleware overhead), no per-request check, clean URL namespace. Tradeoff: requires restart for SG changes. |
| 4 | **`FeatureRequired` returns class, not instance** | DRF's `permission_classes` mechanism requires classes. Factory pattern with baked-in feature path is the cleanest solution. |
| 5 | **`FeatureDisabled` vs `PermissionDenied`** | Frontend needs distinct codes: "feature not available" (config off) vs "you lack access" (RBAC denial). Both 403, different `error.code`. |
| 6 | **`effective_limit()` for dual-source** | Config is the deployment ceiling. Model is the per-account cap. Taking the tighter prevents config from overriding per-account restrictions. |
| 7 | **`pytest_configure` hook for test baseline** | URL assembly runs at import time during collection. Session fixtures run too late. `pytest_configure(trylast=True)` runs after Django setup but before collection. |

---

## Appendix: File Index

| File | Purpose | Key Lines |
|------|---------|-----------|
| `apps/core/feature_config.py` | Core singleton | All 10 public methods (170 lines) |
| `apps/core/exceptions/domain.py` | FeatureDisabled, BusinessRuleViolation, AccountLocked | 177-202, 352-387, 472-481 |
| `apps/core/permissions/base.py` | FeatureRequired factory | 287-328 |
| `apps/core/exceptions/handler.py` | STATUS_CODE_MAP | 70-96 |
| `backend_core/urls/__init__.py` | URL coordinator | GATED_GROUPS (23-31), assembly (46-88) |
| `backend_core/urls/base.py` | Always-on routes | 17-35 |
| `backend_core/urls/organization.py` | Business + platform routes | org_mode logic (14-28) |
| `backend_core/routing.py` | WebSocket routing | chat SG check (9) |
| `deployment_config.json` | Dev config (all ON) | 123 fields |
| `conftest.py` | Test infrastructure | _FULL_FEATURE_CONFIG (22-199), fixtures (202-271) |
