# Feature Gate Developer Guide

> How to add feature gates when building new features.
> For the complete system reference, see `feature-gate-system.md`.

---

## 1. When to Add Gates

Use this decision tree when building something new:

```
New app/system?
  ├─ YES → SG (System Gate) + FG (Feature Gates) + VG (Value Gates)
  └─ NO
       New sub-feature in existing app?
         ├─ YES → FG (Sub-Feature Gate) + VG (if limits/config)
         └─ NO
              New limit or tunable value?
                ├─ YES → VG (Limit or Config Value)
                └─ NO → No gate needed
```

**Rule of thumb**: If a deployment might want it disabled, gate it.

---

## 2. Adding a System Gate (SG)

System Gates control whether an entire system's URLs, admin, tasks, and handlers are registered. When OFF, Django returns natural 404 for all paths in that system.

### Step-by-Step

#### 2.1 Create URL group file

Create `backend_core/urls/<system>.py`:

```python
"""
<System> URL routes.

Gated by systems.<system> in deployment config.
"""

from django.urls import include, path

urlpatterns = [
    path(
        "api/v1/<system>/",
        include("apps.<app>.urls", namespace="<app>"),
    ),
]
```

See `backend_core/urls/network.py` for a minimal example, or `backend_core/urls/organization.py` for one with internal org_mode logic.

#### 2.2 Register in GATED_GROUPS

Edit `backend_core/urls/__init__.py`:

```python
GATED_GROUPS = {
    # ... existing entries ...
    "<system>": lambda fc: fc.is_system_enabled("<system>"),
}
```

Then add the conditional import in the assembly section:

```python
if "<system>" in _enabled:
    from .<system> import urlpatterns as <system>_patterns
    urlpatterns += <system>_patterns
```

#### 2.3 Guard Celery tasks

In `apps/<app>/tasks.py`, add an early return at the top of each task:

```python
from apps.core.feature_config import feature_config

@shared_task
def my_periodic_task():
    if not feature_config.is_system_enabled("<system>"):
        return
    # ... task logic ...
```

#### 2.4 Guard outcome handlers (if applicable)

If your system registers transaction outcome handlers, wrap the registration:

```python
# apps/<app>/outcome_handlers.py
from apps.core.feature_config import feature_config

if feature_config.is_system_enabled("<system>"):
    OutcomeHandlerRegistry.register("my_type", MyHandler)
```

See `apps/transaction/outcome_handlers.py:312` for the network handler example.

#### 2.5 Guard admin registration

In `apps/<app>/apps.py`:

```python
class MyAppConfig(AppConfig):
    name = "apps.<app>"

    def ready(self):
        from apps.core.feature_config import feature_config

        if feature_config.is_system_enabled("<system>"):
            from django.contrib import admin  # noqa: F401
            # Admin auto-discovery happens via Django's admin.autodiscover()
```

#### 2.6 Guard WebSocket consumers (if applicable)

In `backend_core/routing.py`:

```python
if feature_config.is_system_enabled("<system>"):
    from apps.<app>.consumers import MyConsumer
    websocket_urlpatterns.append(path("ws/<path>/", MyConsumer.as_asgi()))
```

#### 2.7 Add to config files

**Both files must be updated:**

1. `backend/deployment_config.json` — add `"<system>": true` under `systems`
2. `backend/conftest.py` — add `"<system>": True` under `_FULL_FEATURE_CONFIG["systems"]`

#### 2.8 Add tests

Add to `apps/core/tests/test_url_groups.py`:

```python
class TestMySystemGroup:
    def test_enabled_when_system_on(self, feature_config_override):
        feature_config_override({"systems": {"<system>": True}})
        enabled = get_enabled_groups(feature_config)
        assert "<system>" in enabled

    def test_disabled_when_system_off(self, feature_config_override):
        feature_config_override({"systems": {"<system>": False}})
        enabled = get_enabled_groups(feature_config)
        assert "<system>" not in enabled
```

---

## 3. Adding a Module Gate (FG)

Module Gates block entire views/endpoints when a feature is disabled. They use `FeatureRequired("path")` in `permission_classes`.

### Pattern A: Static (class-level)

Most common. Use when the entire view should be gated:

```python
from apps.core.permissions.base import FeatureRequired

class MyListView(APIView):
    permission_classes = [IsAuthenticated, FeatureRequired("business.my_feature.enabled")]
```

### Pattern B: Method-level override

Use when only specific HTTP methods need gating (e.g., GET is public, POST needs feature):

```python
class MyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        self.permission_classes = [
            IsAuthenticated,
            FeatureRequired("business.members.enabled"),
        ]
        self.check_permissions(request)
        # ... continue with logic
```

### Pattern C: Shared constant

Use when many views share the same gate:

```python
_MyGate = FeatureRequired("platform.cms")

class View1(APIView):
    permission_classes = [IsAuthenticated, _MyGate]

class View2(APIView):
    permission_classes = [IsAuthenticated, _MyGate]
```

### Pattern D: Mixin with gate map

Use for views that serve multiple scopes (e.g., business forms vs platform forms):

```python
_FORMS_GATE_PATHS = {
    "business": "business.forms.enabled",
    "platform": "platform.forms",
}

class FormViewMixin:
    def _check_feature_gate(self):
        scope = self._get_scope()
        gate_path = _FORMS_GATE_PATHS.get(scope)
        if gate_path:
            self.permission_classes = [IsAuthenticated, FeatureRequired(gate_path)]
            self.check_permissions(self.request)
```

### Config and Tests

1. Add feature path to `deployment_config.json` AND `_FULL_FEATURE_CONFIG`
2. Add test in `apps/core/tests/test_fg_module_gates.py`:

```python
@pytest.mark.django_db
class TestMyFeatureGate:
    def test_returns_403_when_disabled(self, api_client, user, feature_config_override):
        feature_config_override({"business": {"my_feature": {"enabled": False}}})
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/my-endpoint/")
        assert response.status_code == 403
        assert response.data["error"]["code"] == "feature_disabled"
```

---

## 4. Adding a Sub-Feature Gate (FG)

Sub-feature gates provide granular control within a service. They check `is_feature_enabled()` and raise `FeatureDisabled` or return gracefully.

### Pattern A: Raise on disabled

Most common. Used in service methods:

```python
from apps.core.feature_config import feature_config
from apps.core.exceptions import FeatureDisabled

class MyService:
    @staticmethod
    def do_something():
        if not feature_config.is_feature_enabled("business.my_feature.sub_feature"):
            raise FeatureDisabled(feature="business.my_feature.sub_feature")
        # ... feature logic
```

### Pattern B: Graceful skip

Used in search/explore where disabling a sub-feature should return empty results, not an error:

```python
# In a view
users = []
if feature_config.is_feature_enabled("user.explore.search_users"):
    users = ExploreSelector.search_users(q=query)
# Return empty list if disabled — no error
```

### Pattern C: Feature gate maps

Used in transaction services where many types share the same gate pattern:

```python
_INVITATION_FEATURE_GATES = {
    "business_membership_invitation": "business.members.invitations",
    "platform_membership_invitation": "platform.members.invitations",
}

def _check_sub_feature_gates(self, transaction_type):
    gate_path = _INVITATION_FEATURE_GATES.get(transaction_type)
    if gate_path and not feature_config.is_feature_enabled(gate_path):
        raise FeatureDisabled(feature=gate_path)
```

### Config and Tests

1. Add feature path to `deployment_config.json` AND `_FULL_FEATURE_CONFIG`
2. Add test in `apps/core/tests/test_fg_sub_feature_gates.py`:

```python
@pytest.mark.django_db
class TestMySubFeatureGate:
    def test_raises_feature_disabled(self, feature_config_override):
        feature_config_override({"business": {"my_feature": {"sub_feature": False}}})
        with pytest.raises(FeatureDisabled):
            MyService.do_something()
```

---

## 5. Adding a Limit (VG)

### Pattern A: Config-only limit

Use when only the deployment config defines the limit:

```python
from apps.core.feature_config import feature_config

class MyService:
    @staticmethod
    def create_item(account_id):
        current_count = Item.objects.filter(account_id=account_id).count()
        feature_config.check_limit(
            "business.my_feature.max_items",
            current_count,
            rule="item_limit_reached",
            resource="Items",
        )
        # ... create logic
```

`check_limit()` does nothing if limit is 0 (unlimited). If `current >= limit`, raises `BusinessRuleViolation(rule="item_limit_reached", limit=N, current=M)`.

### Pattern B: Dual-source limit (config + model)

Use when both config AND a model field define the same limit:

```python
from apps.core.feature_config import feature_config, FeatureConfig

class MyService:
    @staticmethod
    def create_member(account):
        config_limit = feature_config.get_limit("business.members.max_members", default=0)
        model_limit = account.max_members  # from DB model field
        effective = FeatureConfig.effective_limit(config_limit, model_limit)

        if effective > 0:
            current = Member.objects.filter(account=account).count()
            if current >= effective:
                raise BusinessRuleViolation(
                    message=f"Member limit reached ({effective})",
                    rule="member_quota_exceeded",
                    limit=effective,
                    current=current,
                )
```

### Config and Tests

1. Add limit path (default `0` = unlimited) to `deployment_config.json` AND `_FULL_FEATURE_CONFIG`
2. Add test in `apps/core/tests/test_vg_limits.py`:

```python
@pytest.mark.django_db
class TestMyLimit:
    def test_enforces_limit(self, feature_config_override):
        feature_config_override({"business": {"my_feature": {"max_items": 5}}})
        # Create 5 items, then assert 6th raises
        with pytest.raises(BusinessRuleViolation) as exc:
            MyService.create_item(account_id)
        assert exc.value.details["rule"] == "item_limit_reached"
        assert exc.value.details["limit"] == 5

    def test_unlimited_when_zero(self, feature_config_override):
        feature_config_override({"business": {"my_feature": {"max_items": 0}}})
        # Should not raise even with many items
        MyService.create_item(account_id)
```

---

## 6. Adding a Config Value (VG)

### Pattern A: Replace hardcoded constant

```python
# BEFORE (hardcoded):
MAX_MESSAGE_LENGTH = 5000

# AFTER (configurable):
from apps.core.feature_config import feature_config

max_length = feature_config.get_value("chat.messages.max_length", 5000)
```

### Pattern B: Behavioral boolean

For on/off config values that control behavior (not feature access):

```python
# Uses is_feature_enabled for bool convenience:
if feature_config.is_feature_enabled("network.follow_approval_required"):
    # Require approval even for public businesses
    ...
```

### Config and Tests

1. Add value path with appropriate default to `deployment_config.json` AND `_FULL_FEATURE_CONFIG`
2. Add test in `apps/core/tests/test_vg_config_values.py`:

```python
class TestMyConfigValue:
    def test_uses_config_value(self, feature_config_override):
        feature_config_override({"chat": {"messages": {"max_length": 100}}})
        # Assert the value is used (e.g., validation rejects message > 100 chars)

    def test_uses_default_when_missing(self, feature_config_override):
        feature_config_override({"chat": {}})  # no messages key
        # Assert default value (5000) is used
```

---

## 7. Test Patterns

### The `feature_config_override` Fixture

Available globally from `backend/conftest.py`. Deep-merges overrides into the baseline config, restores after test.

```python
def test_my_gate(feature_config_override):
    # Disable a single feature — all others remain ON
    feature_config_override({"business": {"network": {"enabled": False}}})

    # Test that the gate works
    with pytest.raises(FeatureDisabled):
        NetworkService.create_follow(...)
```

### Testing SG Gates

SG tests are special because URL assembly happens at import time. Use the existing patterns in `test_url_groups.py` — they test `get_enabled_groups()` as a pure function:

```python
def test_my_system_excluded_when_off(self, feature_config_override):
    feature_config_override({"systems": {"my_system": False}})
    from apps.core.feature_config import feature_config
    enabled = get_enabled_groups(feature_config)
    assert "my_system" not in enabled
```

### Testing FG Gates via API

```python
@pytest.mark.django_db
class TestMyFeatureGateApi:
    def test_returns_403_when_disabled(self, api_client, user, feature_config_override):
        feature_config_override({"user": {"my_feature": False}})
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/my-endpoint/")
        assert response.status_code == 403
        assert response.data["error"]["code"] == "feature_disabled"
        assert response.data["error"]["details"]["feature"] == "user.my_feature"
```

### Testing VG Limits via Service

```python
@pytest.mark.django_db
class TestMyLimit:
    def test_raises_at_limit(self, feature_config_override):
        feature_config_override({"business": {"max_items": 2}})
        MyService.create_item(...)  # 1st — OK
        MyService.create_item(...)  # 2nd — OK
        with pytest.raises(BusinessRuleViolation) as exc:
            MyService.create_item(...)  # 3rd — raises
        assert exc.value.details["rule"] == "item_limit_reached"
```

---

## 8. Quick Reference Checklist

When building a new feature, verify each applicable item:

### New System (app)
- [ ] URL group file created in `backend_core/urls/`
- [ ] Entry added to `GATED_GROUPS` in `urls/__init__.py`
- [ ] Conditional import added in assembly section
- [ ] Celery tasks guarded with `is_system_enabled()`
- [ ] Outcome handlers guarded (if transaction-related)
- [ ] Admin registration guarded in `apps.py` `ready()`
- [ ] WebSocket consumers guarded in `routing.py` (if applicable)
- [ ] `systems.<name>: true` added to `deployment_config.json`
- [ ] `systems.<name>: True` added to `_FULL_FEATURE_CONFIG` in `conftest.py`
- [ ] SG tests added

### New Feature/View
- [ ] `FeatureRequired("path")` in `permission_classes` (or method-level)
- [ ] Feature path added to `deployment_config.json`
- [ ] Feature path added to `_FULL_FEATURE_CONFIG`
- [ ] FG module gate test added

### New Sub-Feature
- [ ] `is_feature_enabled("path")` check + `raise FeatureDisabled` in service
- [ ] Feature path added to both config files
- [ ] FG sub-feature gate test added

### New Limit
- [ ] `check_limit()` or `effective_limit()` call in service
- [ ] Limit path (default 0) added to both config files
- [ ] VG limit test added

### New Config Value
- [ ] `get_value("path", default)` replacing hardcoded constant
- [ ] Value path + default added to both config files
- [ ] VG config value test added

---

## 9. Common Mistakes

### Forgetting to update `_FULL_FEATURE_CONFIG`

**Symptom**: Existing tests start failing with 403 or FeatureDisabled errors.

**Fix**: Always add new paths to BOTH `deployment_config.json` (dev default) AND `_FULL_FEATURE_CONFIG` in `backend/conftest.py`.

### Forgetting to update `deployment_config.json`

**Symptom**: Feature works in tests but returns 403 in dev server.

**Fix**: Add the feature path to `deployment_config.json` with appropriate default.

### Using `FeatureRequired()` as instance

**Symptom**: `TypeError` during DRF permission checking.

**Why**: DRF does `[perm() for perm in permission_classes]` — it expects classes, not instances. `FeatureRequired("path")` returns a class. Don't do `FeatureRequired("path")()`.

### Not guarding Celery tasks

**Symptom**: Task runs and accesses models/services that don't exist in minimal deployment.

**Fix**: Add `if not feature_config.is_system_enabled("name"): return` at the top of every task in a gated system.

### Testing SG with wrong timing

**Symptom**: Tests see URLs that should be excluded, or vice versa.

**Why**: URL assembly runs at import time during pytest collection. Session fixtures run too late.

**Fix**: SG tests should test `get_enabled_groups()` as a pure function, not URL resolution. The `pytest_configure` hook handles baseline config.

### Using wrong fixture location

**Symptom**: `feature_config_override` fixture not found.

**Fix**: Feature gate fixtures live in root `backend/conftest.py`, NOT in `backend/tests/conftest.py`. They need to be globally available.

### Mixing up `is_feature_enabled` default

**Symptom**: Feature accidentally enabled in minimal deployment.

**Fix**: `is_feature_enabled()` defaults to `False`. If the path doesn't exist in config, the feature is OFF. This is intentional (minimal-by-default).

---

## 10. Reference

- **Implementation Reference**: `docs/implementations/backend/feature-gate-system.md`
- **Deployment Configuration Guide**: `docs/setup/deployment-configuration.md`
- **Core module**: `apps/core/feature_config.py`
- **Config file**: `deployment_config.json`
- **Annotated example**: `docs/descriptions/backend/deployment_config_full_example.json`
- **Test baseline**: `backend/conftest.py`
