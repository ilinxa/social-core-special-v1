# Feature Gate System — Implementation Plan

## Context

We have a white-label SaaS platform deployed separately per client. A single deployment JSON config file (`deployment_config.json`) controls which features are enabled/disabled. The config file is already designed (142 fields across 15 sections). Now we need to decide **what "disabled" means** at each level and implement the enforcement consistently across the codebase.

**Goal**: Minimum code changes, maximum consistency. When a feature is `false`, the system should behave professionally — clear errors, no crashes, no orphan UI.

### Terminology — Feature Gate vs Content Visibility

This system uses **SG/FG/VG** labels for its three gate levels. These are deliberately different from the Content Visibility System's **T1/T2/T3** tiers to avoid confusion:

| Feature Gate System | Content Visibility System |
|---------------------|--------------------------|
| **SG** (System Gate) — system on/off at startup | **T1** — Always Public fields |
| **FG** (Feature Gate) — feature on/off at runtime | **T2** — Conditional fields (owner-configurable) |
| **VG** (Value Gate) — limits & config values | **T3** — Always Private fields (members + RBAC) |

The two systems are **complementary, not overlapping**. Feature gates control which endpoints/features exist in a deployment. Content visibility controls which fields a viewer sees on a resource.

### Key Decisions (confirmed by user)

1. **SG gates hide from schema**: Disabled systems excluded from both URLs AND OpenAPI schema. Since drf-spectacular auto-generates from registered URLs, removing URL patterns automatically hides them from Swagger/ReDoc — no extra work needed.

2. **Config overrides model**: Deployment config is the **ceiling**. If `business.members.requests = false` in config, it's off even if `BusinessAccount.open_member_request = True` in the DB. Config sets deployment-wide policy; model-level toggles are per-instance preferences within that policy.

3. **Minimal-by-default**: Missing or empty config file → **most restrictive deployment** (all systems OFF, org_mode=user_only, all FG gates OFF). Only Layer 0 foundation (auth, users, email, notifications, rbac) is active. Features must be explicitly enabled in the config file. This is the correct default for a white-label SaaS — each client gets only what they've licensed.

4. **Phase-by-phase implementation**: Implement Phase 1 (foundation) first, validate it, then proceed phase by phase.

---

## Part 1: Feature Gate Categories (The Vocabulary)

Five categories — each with a consistent, predictable behavior.

### Category A — System Gates (SG): "The system doesn't exist here"

**Config keys**: `systems.transaction`, `systems.forms`, `systems.network`, `systems.chat`, `systems.cms`, `systems.explore`, plus `org_mode`

| Aspect | Behavior |
|--------|----------|
| **URLs** | NOT registered → Django returns **404** naturally |
| **OpenAPI schema** | Endpoints absent (drf-spectacular only discovers registered URLs) |
| **HTTP response** | Standard 404 (no custom body — the path simply doesn't exist) |
| **Service layer** | Outcome handlers NOT registered at startup |
| **Celery tasks** | Skipped (early return with structured log) |
| **Admin** | Model admin not registered (conditional import in `apps.py`) |
| **DB tables** | Still exist (apps stay in INSTALLED_APPS for migration safety) |
| **RBAC permissions** | Still seeded (harmless rows — no orphan issues) |
| **Frontend** | Endpoints return 404 → feature routes/UI not rendered |
| **Restart required** | **YES** — SG gates read at startup, affect URL routing |

**Why 404 not 403**: The system literally doesn't exist in this deployment. There's nothing to be "forbidden" from — it's as if the URL was never created. Same pattern as `if settings.DEBUG:` for API docs.

**Org mode effects**:
- `user_only` → business URLs (404) + platform URLs (404) + 6 business-context txn types + 7 platform-context txn types disabled (13 total, leaving only `user_connection_request`)
- `user_and_platform` → business URLs (404) + 6 business-context txn types disabled (3 business-named types with PLATFORM context remain: `business_verification_request`, `business_creation_permission_request`, `business_platform_connection_request`)
- `full` → everything available

**URL directory structure** — routes are split into group files under `backend_core/urls/`:

```
backend_core/urls/
├── __init__.py          ← coordinator: reads config, assembles urlpatterns
├── base.py              ← always-on routes (auth, users, email, notifications, rbac)
├── organization.py      ← business + platform routes (gated by org_mode)
├── transaction.py       ← transaction routes (gated by systems.transaction)
├── forms.py             ← form builder routes (gated by systems.forms)
├── cms.py               ← CMS admin + public routes (gated by systems.cms)
├── explore.py           ← explore/search routes (gated by systems.explore)
├── network.py           ← follow/connection routes (gated by systems.network)
├── chat.py              ← chat routes (gated by systems.chat)
└── dev.py               ← swagger, redoc, silk (gated by DEBUG)
```

**Gated URL routes (9 conditional routes)**:
| Route | SG Gate | Group File |
|-------|---------|------------|
| `/api/v1/platform/` | `org_mode ∈ {full, user_and_platform}` | `organization.py` |
| `/api/v1/business/` | `org_mode == full` | `organization.py` |
| `/api/v1/transactions/` | `systems.transaction` | `transaction.py` |
| `/api/v1/forms/` | `systems.forms` | `forms.py` |
| `/api/v1/cms/admin/` | `systems.cms` | `cms.py` |
| `/api/v1/cms/public/` | `systems.cms` | `cms.py` |
| `/api/v1/explore/` | `systems.explore` | `explore.py` |
| `/api/v1/network/` | `systems.network` | `network.py` |
| `/api/v1/chat/` | `systems.chat` | `chat.py` |

**Always-on routes (5 — Layer 0 foundation, in `base.py`)**:
| Route | App | Why always-on |
|-------|-----|---------------|
| `/api/v1/auth/` | auth | Login/register required always |
| `/api/v1/users/` | users | User identity required always |
| `/api/v1/email/` | email | Password reset, verification |
| `/api/v1/notifications/` | notifications | Security alerts always needed |
| `/api/v1/rbac/` | rbac | Permission list (shared infra) |

---

### Category B — Module Feature Gates (FG): "This feature is turned off"

**Config keys**: Booleans inside account-type scopes that control whether a module is available.

**Two formats in config** (both handled by `is_feature_enabled()`):
- Nested: `business.network.enabled` (has sub-features)
- Simple: `business.cms`, `platform.network`, `platform.forms`, `user.forms` (no sub-features)

| Aspect | Behavior |
|--------|----------|
| **URLs** | Still registered (to return a proper error, not a mystery 404) |
| **HTTP response** | **403** with code `feature_disabled` |
| **Error body** | `{"error": {"message": "This feature is not available", "code": "feature_disabled", "details": {"feature": "business.network"}}}` |
| **Service layer** | Raises `FeatureDisabled` exception |
| **Frontend** | Gets 403 → shows "not available" state; `_permissions` returns `false` for related actions |
| **Config overrides model** | If config says `false`, feature is off regardless of model-level toggles |
| **Restart required** | **NO** — can change at runtime |

**Why 403 not 404**: The URL exists, the system exists, but this feature is disabled in the deployment. 403 tells the client "this endpoint exists, it's just not available." The distinct code `feature_disabled` (vs `permission_denied`) lets the frontend differentiate "feature not available" from "you don't have permission."

**Complete FG Module Gate inventory** (21 gates):

| Config Path | Format | Controls |
|-------------|--------|----------|
| `user.can_create_business` | simple bool | Business creation for users |
| `user.can_be_member` | simple bool | Can join businesses/platform |
| `user.profile_visibility` | simple bool | Visibility override controls |
| `user.forms` | simple bool | Can fill/submit forms |
| `user.network.enabled` | nested | Follow + connection for users |
| `user.chat.enabled` | nested | Chat for users |
| `user.explore.can_explore` | nested | Can use search/discovery |
| `user.transactions.enabled` | nested | Can send/receive transactions |
| `business.members.enabled` | nested | Membership system |
| `business.chat.enabled` | nested | Business-scope chat |
| `business.network.enabled` | nested | Follow + connection for business |
| `business.forms.enabled` | nested | Custom form builder |
| `business.cms` | simple bool | CMS for business |
| `business.transactions.enabled` | nested | Business-level transactions |
| `business.profile_visibility` | simple bool | Visibility override controls |
| `platform.members.enabled` | nested | Platform membership |
| `platform.chat.enabled` | nested | Platform-scope chat |
| `platform.network` | simple bool | Network for platform |
| `platform.forms` | simple bool | Forms for platform |
| `platform.cms` | simple bool | CMS for platform |
| `platform.governance.*` | 4 bools | Approval/verification/moderation |

---

### Category C — Sub-Feature Gates (FG): "This specific capability is off"

**Config keys**: Booleans nested inside a module that control specific capabilities within it.

| Aspect | Behavior |
|--------|----------|
| **URLs** | Parent endpoints work, sub-action blocked |
| **HTTP response** | **403** with code `feature_disabled` |
| **Check location** | **Service layer only** (inside the method that handles the sub-action) |
| **Error body** | Same format as Category B |
| **Frontend** | `_permissions` includes sub-feature flags → UI hides the button/section |

**Complete FG Sub-Feature Gate inventory** (~33 gates):

| Config Path | Parent Module | Controls |
|-------------|---------------|----------|
| `user.network.connections` | user.network | User↔User connections |
| `user.network.follows` | user.network | User→Business/Platform follows |
| `user.chat.group` | user.chat | Group conversations |
| `user.chat.file_sharing` | user.chat | Image attachments |
| `user.chat.reactions` | user.chat | Emoji reactions |
| `user.chat.search` | user.chat | Message search |
| `user.explore.search_users` | user.explore | Can search for users |
| `user.explore.search_businesses` | user.explore | Can search for businesses |
| `user.explore.is_discoverable` | user.explore | Can be found by others |
| `user.profile_default_public` | user | Default profile visibility |
| `business.members.invitations` | business.members | Can send invitations |
| `business.members.requests` | business.members | Can receive join requests |
| `business.members.custom_roles` | business.members | Can create custom roles |
| `business.chat.entity` | business.chat | Business as chat participant |
| `business.chat.group` | business.chat | Group chats in business scope |
| `business.chat.file_sharing` | business.chat | File sharing in business chat |
| `business.network.followers` | business.network | Users can follow business |
| `business.network.connections` | business.network | Business↔Business connections |
| `business.forms.transaction_mapping` | business.forms | Require forms for transactions |
| `business.transactions.verification` | business.transactions | Business verification workflow |
| `business.transactions.ownership_transfer` | business.transactions | Ownership transfer |
| `business.explore.is_discoverable` | business.explore | Appear in explore/search |
| `business.profile_default_public` | business | Default profile visibility |
| `platform.members.invitations` | platform.members | Platform invitations |
| `platform.members.requests` | platform.members | Platform join requests |
| `platform.members.custom_roles` | platform.members | Custom platform roles |
| `platform.chat.entity` | platform.chat | Platform as chat participant |
| `platform.explore.is_discoverable` | platform.explore | Appear in explore/search |
| `platform.transactions.ownership_transfer` | platform.transactions | Platform ownership transfer |
| `platform.governance.business_approval` | platform.governance | Business creation approval |
| `platform.governance.business_verification` | platform.governance | Business verification |
| `platform.governance.approved_creators` | platform.governance | Approved creators list |
| `platform.governance.global_moderation` | platform.governance | Cross-account moderation |

**Note on `platform.transactions`**: The config has `platform.transactions.ownership_transfer` as a sub-feature gate but no `platform.transactions.enabled` module gate. This is intentional — platform transactions only contain one sub-feature (ownership transfer), so a separate module-level toggle would be redundant. The sub-feature gate alone provides sufficient control. This is the only exception to the "every sub-feature has a parent module gate" pattern.

---

### Category D — Limits (VG): "You've hit the cap"

**Config keys**: Numeric values where 0 = unlimited.

| Aspect | Behavior |
|--------|----------|
| **HTTP response** | **400** with code `business_rule_violation` |
| **Error body** | `{"error": {"message": "...", "code": "business_rule_violation", "details": {"rule": "..._exceeded", "limit": 5, "current": 5}}}` |
| **Check location** | Service layer (existing pattern: `_check_member_quota()`) |
| **Frontend** | Shows limit info, disables "add" actions |

**Complete VG Limit inventory** (16 limits):

| Config Path | Default | Existing? |
|-------------|---------|-----------|
| `limits.max_users` | 0 | NEW |
| `limits.max_businesses` | 0 | NEW |
| `limits.max_businesses_per_user` | 1 | NEW |
| `user.max_memberships` | 0 | NEW |
| `user.network.max_connections` | 0 | NEW |
| `user.network.max_follows` | 0 | NEW |
| `user.chat.max_groups` | 0 | NEW |
| `user.transactions.max_pending` | 0 | NEW |
| `business.members.max_members` | 1 | EXISTS (BusinessAccount.max_members) |
| `business.members.max_roles` | 0 | NEW |
| `business.chat.max_groups` | 0 | NEW |
| `business.network.max_followers` | 0 | NEW |
| `business.network.max_connections` | 0 | NEW |
| `business.forms.max_forms` | 0 | NEW |
| `platform.members.max_members` | 5 | EXISTS (PlatformAccount.max_members) |
| `platform.members.max_roles` | 0 | NEW |

---

### Category E — Config Values (VG): "Use this number instead of the hardcoded one"

**Config keys**: Numeric, string, enum, and array values that parameterize system behavior. Also includes **behavioral booleans** in root-level config sections that configure HOW a system works (not WHETHER it's available per account type).

| Aspect | Behavior |
|--------|----------|
| **No blocking** | Pure parameterization — replaces hardcoded constants |
| **Check location** | Wherever the value is used (model methods, services, constants) |
| **Pattern** | `feature_config.get_value("auth.verification.expiry_minutes", 15)` |
| **Restart** | Model-level values at startup; service-level values at runtime |

**Behavioral booleans classified as VG Config** (not FG gates):
These live in root-level config sections and configure behavior within an already-enabled system:

| Config Path | Default | Why VG not FG |
|-------------|---------|---------------|
| `chat.requests.enabled` | true | Configures chat request workflow, not chat on/off |
| `network.follow_approval_required` | false | Configures approval flow, not network on/off |
| `network.connection_approval_required` | true | Same |
| `auth.signup.email_password` | true | Configures signup method, not auth on/off |
| `auth.signup.email_verification_required` | true | Same |
| `auth.oauth.google` | true | Configures OAuth provider, not auth on/off |
| `auth.oauth.apple` | true | Same |
| `notifications.email_enabled` | true | Configures notification channel |
| `notifications.push_enabled` | false | Same |
| `notifications.sms_enabled` | false | Same |
| `explore.suggested_tags_enabled` | true | Configures explore behavior |
| `infra.sentry_enabled` | false | Configures infrastructure |

**Remaining config values**: ~37 numeric/string/enum/array values across auth, chat, cms, transaction, network, explore, notifications, infra sections.

---

## Part 2: Implementation Architecture

### New Components (minimal — 2 new files, 5 edited files)

#### 1. Config Loader — `backend/apps/core/feature_config.py` (NEW ~150 lines)

Single module. Singleton pattern. Loads JSON config once at startup, provides typed access.

```
FeatureConfig
├── _load_config(path)       — reads JSON, returns dict (or empty dict if missing)
├── get(dotted_key, default) — traverse nested dict: "systems.chat" → True/False
├── is_system_enabled(name)  — shorthand: get("systems.{name}", False)      [SG]
├── is_feature_enabled(path) — FG check: get(path, False) — both nested and simple bools
├── get_limit(path, default) — VG numeric: get(path, default), treats 0 as unlimited
├── get_value(path, default) — VG generic: get(path, default) for any type
├── get_org_mode()           — get("org_mode", "user_only")
├── has_business()           — org_mode == "full"
├── has_platform()           — org_mode in ("full", "user_and_platform")
├── effective_limit(config_limit, model_limit) — min of two limits (0=unlimited)
└── reload()                 — re-read config file (for FG/VG runtime changes)
```

**`effective_limit()` — config-vs-model limit resolution**:

When both deployment config and a model field define a limit for the same thing (e.g., `max_members`), the effective limit is the tighter of the two, treating 0 as unlimited:

```python
@staticmethod
def effective_limit(config_limit: int, model_limit: int) -> int:
    """Return the tighter of two limits. 0 means unlimited in both."""
    if config_limit == 0 and model_limit == 0:
        return 0  # both unlimited
    if config_limit == 0:
        return model_limit  # config unlimited, model sets limit
    if model_limit == 0:
        return config_limit  # model unlimited, config sets limit
    return min(config_limit, model_limit)  # both set, take tighter
```

This is used in Phase 5 for the 2 existing limits that have both config and model values:
- `business.members.max_members` (config) vs `BusinessAccount.max_members` (model, default=1)
- `platform.members.max_members` (config) vs `PlatformAccount.max_members` (model, default=5)

**Config file location**: `DEPLOYMENT_CONFIG_PATH` env var → defaults to `backend/deployment_config.json`

**Default behavior**: Missing file → empty dict → ALL defaults apply → **minimal deployment**. Only Layer 0 foundation (auth, users, email, notifications, rbac) is active. All systems OFF, org_mode=user_only, all FG gates OFF. **Enable features explicitly in the config file.**

**Why minimal-by-default**: This is a white-label SaaS — each client deployment should include only the features they've licensed. A missing or empty config file means "nothing is configured yet," which should result in the most restrictive state, not the most permissive. The config file is the explicit contract of what's enabled.

**Handles both config formats**:
```python
# Nested (has sub-features): traverses to .enabled
feature_config.is_feature_enabled("business.network.enabled")  # → False (if not in config)

# Simple boolean (no sub-features): returns the bool directly
feature_config.is_feature_enabled("business.cms")  # → False (if not in config)

# With config file that sets them to true:
# {"business": {"network": {"enabled": true}, "cms": true}}
feature_config.is_feature_enabled("business.network.enabled")  # → True
feature_config.is_feature_enabled("business.cms")  # → True
```

**Test baseline**: Existing 4000+ unit tests must NOT break. Two mechanisms:

1. **`feature_config_override` fixture** — deep-merges overrides into config for any test:
```python
@pytest.fixture
def feature_config_override():
    """Override feature config for testing."""
    def _override(overrides):
        # Deep-merge overrides into current config
        ...
    return _override
```

2. **Session-scoped auto-use fixture** — sets ALL features ON at test suite startup:
```python
# backend/tests/conftest.py (or apps/core/tests/conftest.py)
@pytest.fixture(autouse=True, scope="session")
def _enable_all_features():
    """All features ON for test suite — matches production-full config.
    Individual tests use feature_config_override() to test disabled scenarios."""
    from apps.core.feature_config import feature_config
    feature_config._config = FULL_FEATURE_CONFIG  # all systems, all features, all limits
    yield
    feature_config._config = {}
```

This ensures: (a) existing tests pass unchanged, (b) feature gate tests explicitly override to test disabled scenarios, (c) no test accidentally relies on a feature being off.

#### 2. FeatureDisabled Exception — `backend/apps/core/exceptions/domain.py` (EDIT ~15 lines)

```python
class FeatureDisabled(DomainException):
    """Feature is disabled by deployment configuration. Maps to HTTP 403."""
    default_message = "This feature is not available"
    default_code = "feature_disabled"

    def __init__(self, message=None, feature=None):
        details = {}
        if feature:
            details["feature"] = feature
        super().__init__(message=message, code=self.default_code, details=details)
```

Add to `STATUS_CODE_MAP` in handler.py: `"feature_disabled": status.HTTP_403_FORBIDDEN`

#### 3. FeatureRequired Permission — `backend/apps/core/permissions/base.py` (EDIT ~30 lines)

**DRF constraint**: `permission_classes` must contain **classes**, not instances. DRF instantiates them via `[permission() for permission in self.permission_classes]`. Putting `FeatureRequired("path")` (an instance) in the list would fail because DRF would call `instance()` → `TypeError`.

**Solution**: Class factory function that returns a **class** (not an instance):

```python
def FeatureRequired(feature_path):
    """
    DRF permission class factory — returns a permission CLASS for a feature path.
    Returns 403 with feature_disabled code when feature is off.

    Usage:
        permission_classes = [IsAuthenticated, FeatureRequired("business.network.enabled")]
        permission_classes = [AllowAny, FeatureRequired("business.cms")]

    DRF calls permission() on each item in permission_classes, so items must be
    classes (not instances). This factory returns a new class each time.
    """

    class _FeatureRequiredPermission(BasePermission):
        _feature_path = feature_path
        message = "This feature is not available"
        code = "feature_disabled"

        def has_permission(self, request, view):
            from apps.core.feature_config import feature_config

            if not feature_config.is_feature_enabled(self._feature_path):
                raise FeatureDisabled(feature=self._feature_path)
            return True

    # Readable class name for debugging and DRF's error messages
    _FeatureRequiredPermission.__name__ = f"FeatureRequired_{feature_path}"
    _FeatureRequiredPermission.__qualname__ = f"FeatureRequired_{feature_path}"
    return _FeatureRequiredPermission
```

**Why this works**: `FeatureRequired("business.cms")` returns a class. DRF instantiates it via `FeatureRequired_business.cms()` → instance with `has_permission()`. This is the same pattern used by `rest_condition` and other DRF permission libraries.

**Why raise instead of return False**: `return False` triggers DRF's generic `PermissionDenied` (code `permission_denied`). By raising `FeatureDisabled` directly, we get the distinct `feature_disabled` code and include `details.feature` in the response body — critical for the frontend to distinguish "feature disabled" from "you lack permission."

Compatible with existing DRF pattern: views use `permission_classes = [IsAuthenticated, FeatureRequired("...")]` — DRF AND's all permissions. Verified against `network/views.py`, `forms/api/views.py`, `explore/views.py` — none of the existing 8 permission classes in `base.py` use `__init__` parameters.

---

### Enforcement Layer Per Category

```
                         URL routing    DRF Permission    Service Layer
                         (urls.py)      (permission_cls)  (service.py)
                         ──────────     ──────────────    ─────────────
Cat A — SG System         ██ HERE        (not reached)     (not reached)
Cat B — FG Module                        ██ HERE           (backup check)
Cat C — FG Sub-feature                                     ██ HERE
Cat D — VG Limits                                          ██ HERE
Cat E — VG Config                                          ██ HERE (value sub)
```

**Principle**: Fail as early as possible, but don't over-engineer.
- SG fails at routing (earliest possible — URL doesn't exist)
- FG module fails at DRF permission (before view logic runs)
- FG sub-feature + VG fail in service (where business logic and counts are available)

---

## Part 3: Implementation Phases

### Phase 1: Foundation (implement first — everything else depends on this)

**Scope**: Config loader + exception + permission class

| Step | File | Change | Lines |
|------|------|--------|-------|
| 1.1 | `apps/core/feature_config.py` | NEW — Config loader singleton | ~150 |
| 1.2 | `apps/core/exceptions/domain.py` | ADD `FeatureDisabled` exception class | ~15 |
| 1.3 | `apps/core/exceptions/handler.py` | ADD `feature_disabled` → 403 mapping | ~2 |
| 1.4 | `apps/core/exceptions/__init__.py` | EXPORT `FeatureDisabled` | ~1 |
| 1.5 | `apps/core/permissions/base.py` | ADD `FeatureRequired` class factory function | ~30 |
| 1.6 | `backend_core/settings/base.py` | ADD `DEPLOYMENT_CONFIG_PATH` setting | ~5 |
| 1.7 | `apps/core/tests/test_feature_config.py` | NEW — Config loader + exception + permission tests | ~250 |

**Key test scenarios**:
- Missing config file → minimal deployment (all systems off, org_mode=user_only, all FG gates off)
- Empty config → minimal deployment (same as missing)
- Full config file → all features ON (matches deployment_config_full_example.json)
- Dot-notation traversal: nested and simple bool formats
- `FeatureDisabled` exception → 403 response with correct body
- `FeatureRequired("path")` returns a CLASS (not instance) — `isinstance(FeatureRequired("x"), type)` is True
- `FeatureRequired` permission blocks when feature off (raises `FeatureDisabled`), passes when on
- Session-scoped auto-use fixture provides all-ON baseline → existing tests unaffected
- `feature_config_override` fixture deep-merges overrides → feature gate tests can disable specific features
- `is_system_enabled()` defaults to `False`, `has_business()` defaults to `False`, `has_platform()` defaults to `False`
- `is_system_enabled()`, `has_business()`, `has_platform()` for all org_mode values
- `effective_limit()` edge cases: both 0, one 0, both non-zero, min selection

**Verify**: Run full existing test suite → ZERO failures (auto-use fixture enables all features).

---

### Phase 2: SG System Gates (org_mode + 6 system gates)

**Scope**: URL directory restructure, outcome handler registration, Celery tasks, WebSocket routing, admin registration

| Step | File(s) | Change |
|------|---------|--------|
| 2.1 | `backend_core/urls/` (NEW directory) | Restructure monolithic `urls.py` into URL group files (see below) |
| 2.2 | `apps/transaction/apps.py` | Gate `register_all_handlers()` — skip network handlers if network system off |
| 2.3 | `apps/transaction/outcome_handlers.py` | Gate network handler imports (lines 314-322) |
| 2.4 | `backend_core/routing.py` | Gate ChatConsumer WebSocket — empty list if chat off |
| 2.5 | 8 Celery tasks | Add early-return: 4 transaction, 2 CMS, 2 chat tasks |
| 2.6 | 5 `apps.py` files | Gate admin imports: network, forms, cms, explore, chat |
| 2.7 | Tests | SG gate tests (3-level strategy — see below) |

#### Step 2.1 Detail: URL Directory Architecture

Replace monolithic `backend_core/urls.py` with `backend_core/urls/` package (10 files):

| File | Contents | Gating |
|------|----------|--------|
| `__init__.py` | Coordinator — `GATED_GROUPS` dict, `get_enabled_groups()`, assembles `urlpatterns` | Config-driven |
| `base.py` | auth, users, email, notifications, rbac + health/admin | Always included |
| `organization.py` | business + platform routes | `org_mode` |
| `transaction.py` | transaction routes | `systems.transaction` |
| `forms.py` | form builder routes | `systems.forms` |
| `cms.py` | CMS admin + public routes | `systems.cms` |
| `explore.py` | explore/search routes | `systems.explore` |
| `network.py` | follow/connection routes | `systems.network` |
| `chat.py` | chat routes | `systems.chat` |
| `dev.py` | swagger, redoc, silk, static media | `settings.DEBUG` |

**Coordinator pattern** — `backend_core/urls/__init__.py`:

```python
from apps.core.feature_config import feature_config
from .base import urlpatterns as base_patterns

# ── Decision layer (testable as pure data) ──────────────────────
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
    """Returns set of enabled group names. Pure function — testable without Django URL loading."""
    fc = fc or feature_config
    return {name for name, check in GATED_GROUPS.items() if check(fc)}

# ── Assembly layer (runs once at startup) ────────────────────────
urlpatterns = list(base_patterns)
enabled = get_enabled_groups()

if "organization" in enabled:
    from .organization import urlpatterns as org_patterns
    urlpatterns += org_patterns
if "transaction" in enabled:
    from .transaction import urlpatterns as txn_patterns
    urlpatterns += txn_patterns
# ... etc for each group

# Dev-only routes
from django.conf import settings
if settings.DEBUG:
    from .dev import urlpatterns as dev_patterns
    urlpatterns += dev_patterns
```

**Organization group** handles `org_mode` granularity internally:

```python
# backend_core/urls/organization.py
from apps.core.feature_config import feature_config

urlpatterns = []

if feature_config.has_platform():
    urlpatterns += [
        path("api/v1/platform/", include("apps.organization.platform.urls", namespace="platform")),
    ]

if feature_config.has_business():
    urlpatterns += [
        path("api/v1/business/", include("apps.organization.business.urls", namespace="business")),
    ]
```

**Each group file** is a simple list of `path()` calls — no conditional logic (except `organization.py`). The coordinator decides whether to include the entire group.

**Migration path**: Delete old `backend_core/urls.py`, create `backend_core/urls/__init__.py`. `ROOT_URLCONF = "backend_core.urls"` remains unchanged — Django resolves it to the package `__init__.py`.

#### Step 2.7 Detail: SG Testing Strategy (3 levels)

URL patterns are built once at module import time. You cannot toggle an SG gate mid-test. Testing is split into 3 levels:

| Level | What | How | Touches Django URLs? |
|-------|------|-----|---------------------|
| **Unit** | `get_enabled_groups()` returns correct sets for each config | Mock `feature_config`, call `get_enabled_groups(fc)` | NO |
| **Unit** | Each group file has correct patterns | Import `urls.{group}.urlpatterns`, inspect list | NO |
| **Integration** | Disabled group → Django returns 404 | One test with separate `ROOT_URLCONF` (test-specific coordinator) | YES (1 test) |

**Unit test for decision logic** (~15 scenarios):
```python
class TestGetEnabledGroups:
    def test_full_mode_all_systems_on(self, feature_config_override):
        """All features enabled — full deployment."""
        feature_config_override({"org_mode": "full", "systems": {
            "transaction": True, "forms": True, "network": True,
            "chat": True, "cms": True, "explore": True,
        }})
        enabled = get_enabled_groups()
        assert enabled == {"organization", "transaction", "forms", "cms", "explore", "network", "chat"}

    def test_empty_config_minimal(self):
        """No config → minimal deployment → nothing enabled."""
        fc = FeatureConfig({})  # empty config
        enabled = get_enabled_groups(fc)
        assert enabled == set()

    def test_user_only_mode(self, feature_config_override):
        feature_config_override({"org_mode": "user_only", "systems": {
            "transaction": True, "network": True,
        }})
        enabled = get_enabled_groups()
        assert "organization" not in enabled
        assert "transaction" in enabled

    def test_chat_off_network_on(self, feature_config_override):
        """Selectively enable network but not chat."""
        feature_config_override({"systems": {"chat": False, "network": True}})
        enabled = get_enabled_groups()
        assert "chat" not in enabled
        assert "network" in enabled
```

**Unit test for group file content** (~9 tests):
```python
class TestUrlGroupFiles:
    def test_base_has_always_on_routes(self):
        from backend_core.urls.base import urlpatterns
        namespaces = {p.namespace for p in urlpatterns if hasattr(p, 'namespace')}
        assert {"authentication", "users", "email", "notifications", "rbac"} <= namespaces

    def test_chat_group_has_chat_routes(self):
        from backend_core.urls.chat import urlpatterns
        assert any("chat" in str(p.pattern) for p in urlpatterns)
```

**Integration test** (1 test — proves the wiring):
Uses a test-specific `ROOT_URLCONF` module that assembles `urlpatterns` with chat excluded, then verifies `/api/v1/chat/` returns 404 while `/api/v1/auth/` returns 200.

**Outcome handler gating detail**:
```
register_all_handlers() — 14 handlers total:
├── ALWAYS registered (8): 4 membership + 1 verification + 2 ownership + 1 permission
└── GATED by systems.network (6): 3 follow + 3 connection handlers
    (forms has 0 outcome handlers — no gating needed)
```

**Admin registration pattern**: Use conditional import in `apps.py`:
```python
# apps/chat/apps.py
def ready(self):
    from apps.core.feature_config import feature_config
    if feature_config.is_system_enabled("chat"):
        import apps.chat.admin  # noqa: F401 — triggers @admin.register
```

---

### Phase 3: FG Module Feature Gates (21 module gates)

**Scope**: Per-account-type feature on/off via DRF permission + service guards

| Step | Files | Gates applied |
|------|-------|---------------|
| 3.1 | `apps/network/views.py` | `FeatureRequired("user.network.enabled")`, `FeatureRequired("business.network.enabled")` |
| 3.2 | `apps/organization/business/views.py` | `business.members.enabled`, `business.transactions.enabled`, `business.profile_visibility` |
| 3.3 | `apps/organization/platform/views.py` | `platform.members.enabled` |
| 3.4 | `apps/forms/api/views.py` | `business.forms.enabled`, `platform.forms`, `user.forms` |
| 3.5 | `apps/cms/api/views.py` | `business.cms`, `platform.cms` |
| 3.6 | `apps/explore/views.py` | `user.explore.can_explore` |
| 3.7 | `apps/users/views.py` | `user.can_create_business`, `user.profile_visibility` |
| 3.8 | Tests | FG gate tests — verify 403 for disabled modules |

---

### Phase 4: FG Sub-Feature Gates (~33 sub-feature gates)

**Scope**: Granular capabilities within modules — ALL checked in service layer only

| Step | Scope | Sub-features gated |
|------|-------|--------------------|
| 4.1 | Chat services | reactions, file_sharing, search, group, entity |
| 4.2 | Network services | connections vs follows (separately per scope) |
| 4.3 | Member services | invitations, requests, custom_roles (config-first check order — see below) |
| 4.4 | Form services | transaction_mapping |
| 4.5 | Transaction services | verification, ownership_transfer |
| 4.6 | Explore services | search_users, search_businesses, is_discoverable |
| 4.7 | Governance services | business_approval, business_verification, approved_creators, global_moderation |
| 4.8 | Tests | Sub-feature gate tests per module |

#### Step 4.3 Detail: Config-First Check Order for Member Services

`business.members.requests` and `business.members.invitations` are sub-feature gates that overlap with existing model-level controls. The config check must come **before** the model check, producing distinct error codes:

**`create_request()` call chain** (current: lines 340-354 of `transaction/services.py`):
```
Current:                           After Phase 4:
─────────                          ──────────────
1. _check_open_member_request()    1. config check: business.members.requests → 403 if false
   → model toggle → 400            2. _check_open_member_request()
2. _check_member_quota()              → model toggle → 400 if false
   → model limit → 400             3. _check_member_quota()
                                      → effective_limit() → 400 if exceeded (Phase 5)
```

**`create_invitation()` call chain** (current: lines 162-167):
```
Current:                           After Phase 4:
─────────                          ──────────────
1. _check_member_quota()           1. config check: business.members.invitations → 403 if false
   → model limit → 400             2. _check_member_quota()
                                      → effective_limit() → 400 if exceeded (Phase 5)
```

The config check is a 3-line insert before the existing pre-checks:
```python
if not feature_config.is_feature_enabled(f"{config.context_type}.members.requests"):
    raise FeatureDisabled(feature=f"{config.context_type}.members.requests")
```

---

### Phase 5: VG Limits (16 limits)

**Scope**: Numeric limit enforcement following existing `_check_member_quota()` pattern

| Step | Limits | Pattern |
|------|--------|---------|
| 5.1 | Deployment-wide | max_users, max_businesses, max_businesses_per_user |
| 5.2 | User limits | max_memberships, max_connections, max_follows, max_groups, max_pending |
| 5.3 | Business limits | max_roles, max_forms, max_groups, max_connections, max_followers |
| 5.4 | Platform limits | max_roles |
| 5.5 | Existing limits | Wire `max_members` through `effective_limit()` — shared quota resolution (see below) |
| 5.6 | Tests | Boundary value tests for each limit, including `effective_limit()` edge cases |

#### Step 5.5 Detail: Shared Quota Resolution for `max_members`

Currently `max_members` quota is checked in **two independent places**, both reading only the model field:

| Location | File | Line | What it does |
|----------|------|------|-------------|
| Pre-check | `TransactionService._check_member_quota()` | services.py:1001 | Counts active + pending, compares to `model.max_members` |
| Hard gate | `RBACService.create_membership()` | services.py:346 | Counts active only, compares to `model.max_members` |

Both must be updated to use `effective_limit(config_limit, model_limit)`. To avoid duplication, extract the limit resolution:

```python
# In TransactionService._check_member_quota() and RBACService.create_membership():
# BEFORE (reads model only):
max_members = BusinessAccount.objects.values_list("max_members", flat=True).get(id=account_id)

# AFTER (resolves config vs model):
from apps.core.feature_config import feature_config
model_limit = BusinessAccount.objects.values_list("max_members", flat=True).get(id=account_id)
config_limit = feature_config.get_limit(f"{account_type}.members.max_members", 0)
max_members = feature_config.effective_limit(config_limit, model_limit)
```

**Edge cases tested**:
- Config=0, Model=0 → unlimited (both defer)
- Config=10, Model=0 → 10 (config sets ceiling, model is unlimited)
- Config=0, Model=5 → 5 (config is unlimited, model restricts)
- Config=10, Model=3 → 3 (model is tighter)
- Config=3, Model=10 → 3 (config is tighter)

---

### Phase 6: VG Config Values (~49 values + 12 behavioral booleans)

**Scope**: Replace hardcoded constants with config-driven values

| Step | Domain | Values replaced |
|------|--------|-----------------|
| 6.1 | Auth | verification expiry/code_length, reset expiry, sessions, lockout, OAuth toggles (15 values) |
| 6.2 | Chat | message length, edit window, group size, rate limits, attachments, presence, reactions (16 values) |
| 6.3 | CMS | max versions, folder depth, throttle, rate limit, media types (5 values) |
| 6.4 | Transaction | default expiry, resubmission cooldown, reminder hours (3 values) |
| 6.5 | Network | follow/connection approval required (2 values) |
| 6.6 | Explore | results_per_page, min_search_length, suggested_tags (3 values) |
| 6.7 | Notifications | retention, channel enables (4 values) |
| 6.8 | Infra | email backend, storage backend, admin URL, audit/email retention, sentry (6 values) |
| 6.9 | Tests | Config value override tests |

---

## Part 4: Consistency Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | **SG gates = URL group exclusion** | System off → group file not imported by coordinator → 404. No middleware, no permission class. |
| 2 | **FG module gates = `FeatureRequired` DRF permission** | Applied at view class level. Runs before any view logic. Returns 403 `feature_disabled`. |
| 3 | **FG sub-feature gates = service method check** | Check inside the specific method, not at view level. Raises `FeatureDisabled`. |
| 4 | **VG limits = `BusinessRuleViolation`** | Always with `rule`, `limit`, `current` in details dict. |
| 5 | **VG config = `feature_config.get_value()`** | Never `getattr(settings, ...)` for deployment-config values. |
| 6 | **Config overrides model (check order)** | Check `feature_config` BEFORE model-level toggles. Config disabled → 403 `feature_disabled`. Model disabled → 400 `business_rule_violation`. Different meaning, different code. |
| 7 | **Missing config = minimal** | No config file → minimal deployment (all systems OFF, org_mode=user_only, all FG gates OFF). Only Layer 0 foundation active. Config file is the explicit contract of enabled features. Test suite uses session-scoped auto-use fixture to enable all features. |
| 8 | **SG at startup, FG/VG at runtime** | SG gates affect URL routing (startup). FG/VG read fresh per request. |
| 9 | **All gates testable** | pytest fixture `feature_config_override({...})` for any test. |
| 10 | **Error codes are distinct** | `feature_disabled` (403) ≠ `permission_denied` (403) ≠ `business_rule_violation` (400) ≠ `not_found` (404). Frontend distinguishes all four. |
| 11 | **Root-level config booleans = VG** | Booleans in `auth.*`, `chat.*`, `network.*`, `notifications.*`, `explore.*`, `infra.*` configure behavior. Booleans in `user.*`, `business.*`, `platform.*` gate features. |
| 12 | **Admin uses conditional import** | `@admin.register` decorator pattern → gate by wrapping `import apps.X.admin` in `apps.py:ready()`. |
| 13 | **Dual limits use `effective_limit()`** | When both config and model define a limit (e.g., `max_members`), use `effective_limit(config, model)` → min of non-zero values, 0=unlimited. |
| 14 | **Shared quota resolution** | `_check_member_quota()` (TransactionService) and `create_membership()` (RBACService) both enforce `max_members`. Both must use the same `effective_limit()` logic — never query model limit independently. |

**Rule 6 expanded — config-vs-model check order**:

Three conflict points exist where deployment config and model fields control the same thing:

| Config Path | Model Field | Config Off = | Model Off = |
|-------------|-------------|-------------|------------|
| `business.members.requests` | `BusinessAccount.open_member_request` | 403 `feature_disabled` | 400 `member_requests_closed` |
| `business.members.max_members` | `BusinessAccount.max_members` | `effective_limit()` | `effective_limit()` |
| `platform.members.max_members` | `PlatformAccount.max_members` | `effective_limit()` | `effective_limit()` |

**Boolean toggle check order** (config first):
```
1. feature_config.is_feature_enabled("business.members.requests")
   → if false: raise FeatureDisabled(feature="business.members.requests")    # 403
2. BusinessAccount.open_member_request (from DB)
   → if false: raise BusinessRuleViolation(rule="member_requests_closed")    # 400
3. Proceed with request creation
```

Why both: Config false = "this deployment doesn't support member requests at all" (deployment policy). Model false = "this specific business has requests turned off, but could re-enable" (instance preference). The frontend shows different UI for each.

---

## Part 5: Critical Files

### New Files
| File | Purpose | Est. Lines |
|------|---------|------------|
| `backend/apps/core/feature_config.py` | Config loader singleton | ~150 |
| `backend/apps/core/tests/test_feature_config.py` | Foundation tests (Phase 1) | ~250 |
| `backend_core/urls/__init__.py` | URL coordinator — `GATED_GROUPS`, `get_enabled_groups()`, assembly | ~60 |
| `backend_core/urls/base.py` | Always-on routes (auth, users, email, notifications, rbac, health, admin) | ~30 |
| `backend_core/urls/organization.py` | Business + platform routes (gated by org_mode) | ~20 |
| `backend_core/urls/transaction.py` | Transaction routes | ~10 |
| `backend_core/urls/forms.py` | Form builder routes | ~10 |
| `backend_core/urls/cms.py` | CMS admin + public routes | ~15 |
| `backend_core/urls/explore.py` | Explore/search routes | ~10 |
| `backend_core/urls/network.py` | Network (follow/connection) routes | ~10 |
| `backend_core/urls/chat.py` | Chat routes | ~10 |
| `backend_core/urls/dev.py` | Swagger, redoc, silk, static media | ~25 |
| `backend/apps/core/tests/test_url_groups.py` | SG decision logic + group file tests (Phase 2) | ~150 |
| `backend/apps/core/tests/test_sg_integration.py` | SG integration test with separate ROOT_URLCONF (Phase 2) | ~40 |

### Edited Files (Phase 1 only — ~70 lines of edits)
| File | Change |
|------|--------|
| `backend/apps/core/exceptions/domain.py` | Add `FeatureDisabled` class (~15 lines) |
| `backend/apps/core/exceptions/handler.py` | Add status code mapping (~2 lines) |
| `backend/apps/core/exceptions/__init__.py` | Export `FeatureDisabled` (~1 line) |
| `backend/apps/core/permissions/base.py` | Add `FeatureRequired` class factory (~30 lines) |
| `backend/backend_core/settings/base.py` | Add `DEPLOYMENT_CONFIG_PATH` (~5 lines) |

### Edited Files (Phases 2-6)
| Phase | Files | Est. Changes |
|-------|-------|-------------|
| Phase 2 | `urls/` package (10 files, replaces `urls.py`), `routing.py`, `transaction/apps.py`, `transaction/outcome_handlers.py`, 5 `apps.py`, 8 tasks | ~200 lines (includes URL split) |
| Phase 3 | 7 `views.py` + 1 service | ~50 lines |
| Phase 4 | ~8 `services.py` files | ~80 lines |
| Phase 5 | ~5 service/selector files | ~100 lines |
| Phase 6 | ~12 files (models, constants, services) | ~120 lines |

---

## Part 6: Verification Plan

### Phase 1 Verification
```bash
# 1. Run full existing test suite — ZERO should break
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest --tb=short -q"

# 2. Run new feature_config tests
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest apps/core/tests/test_feature_config.py -v"

# 3. Verify FeatureDisabled exception handling
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest apps/core/tests/test_handler.py -v"
```

### Phase 2 Verification
```bash
# 1. Run full existing test suite — ZERO should break (URL split is a refactor)
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest --tb=short -q"

# 2. Unit tests: get_enabled_groups() decision logic + group file content
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest apps/core/tests/test_url_groups.py -v"

# 3. Integration test: disabled group → 404
powershell -Command "Set-Location backend; & .\venv\Scripts\python.exe -m pytest apps/core/tests/test_sg_integration.py -v"
```

### Per-Phase Verification (Phases 3-6)
Each phase: run its specific tests + full suite → zero regressions.

### Final Integration
```bash
# Full SQLite suite (3589+ unit tests)
python -m pytest -q

# Full PostgreSQL suite (~3630 tests)
python -m pytest -o 'DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker' -q

# API integration tests (296 tests)
make test-api
```

---

## Part 7: Complete Field Inventory

### Summary
| Category | Count | Examples |
|----------|-------|---------|
| Metadata | 11 | deployment.name, deployment.code |
| SG System Gates | 7 | org_mode, systems.transaction |
| FG Module Gates | 21 | user.network.enabled, business.cms |
| FG Sub-Feature Gates | ~33 | user.chat.reactions, business.members.invitations |
| VG Limits | 16 | business.members.max_members, user.network.max_connections |
| VG Config Values | ~49 | auth.verification.expiry_minutes, chat.messages.max_length |
| VG Behavioral Bools | 12 | auth.oauth.google, notifications.email_enabled |
| Special (array) | 3 | business.members.available_permissions, chat.reactions.types |
| **TOTAL** | **~142** | |

---

## Related Documents

- **Deployment Config JSON**: `docs/descriptions/backend/deployment_config_full_example.json` (142 fields, source of truth)
- **Deployment Config Form**: `docs/descriptions/backend/deployment_configuration_form.md` (human-readable field descriptions)
- **Implementation Reference**: `docs/implementations/backend/feature-gate-system.md` (created after Phase 1, updated per phase)
- **Memory**: `memory/feature-gate-system.md` (implementation details per phase)
