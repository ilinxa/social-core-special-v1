# Backend Test Standards

Comprehensive reference for writing and maintaining tests across the Django backend.

## File Structure Per App

```
apps/<app_name>/tests/
    __init__.py
    conftest.py        # Fixtures: clients, users, factories, URLs
    factories.py       # Factory-boy factories for app models
    test_models.py     # Model creation, constraints, properties, managers
    test_services.py   # Business logic (mocking at boundaries)
    test_selectors.py  # Read-only query methods (no mocking)
    test_views.py      # API endpoints (status codes, response format)
    test_tasks.py      # Celery tasks (called directly, not via .delay())
```

Optional files as needed:
- `test_authentication.py` — Custom auth backends
- `test_throttles.py` — Rate limiting configuration
- `test_webhooks.py` — Incoming webhook handlers

## Naming Conventions

### Test Classes

```python
@pytest.mark.django_db
class TestEmailServiceSend:
    """Tests for EmailService.send()."""
```

Format: `Test<Class><Method>` or `Test<Class>` when grouping related methods.

### Test Methods

```python
def test_send_raises_not_found_for_unknown_type(self):
    """send() raises NotFound when notification type is not registered."""
```

Format: `test_<method>_<scenario>` with a docstring describing expected behavior.

### Docstrings

Every test method must have a docstring describing what it verifies. Format:
```
"""<method_name> <expected_behavior> when <condition>."""
```

## Conftest Organization

Every app conftest follows 4 sections with comment headers:

```python
# =============================================================================
# API CLIENT FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, user):
    """Return an APIClient authenticated as a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


# =============================================================================
# USER FIXTURES
# =============================================================================

@pytest.fixture
def user(db):
    """Create and return a regular test user."""
    return UserFactory()


# =============================================================================
# FACTORY FIXTURES
# =============================================================================

@pytest.fixture
def some_factory(db):
    """Return the SomeFactory."""
    return SomeFactory


# =============================================================================
# URL FIXTURES
# =============================================================================

@pytest.fixture
def some_url():
    """Return the endpoint URL."""
    return "/api/v1/some/endpoint/"
```

## Factory Patterns

### Canonical UserFactory

All user factories live in `apps/users/tests/factories.py`. All other apps import from there:

```python
from apps.users.tests.factories import UserFactory, VerifiedUserFactory, StaffUserFactory, SuperuserFactory
```

Never define `UserFactory` anywhere else. Global `tests/factories.py` re-exports for convenience.

### Factory Rules

1. Always set `skip_postgeneration_save = True` in Meta:
   ```python
   class Meta:
       model = SomeModel
       skip_postgeneration_save = True
   ```

2. Use `factory.Sequence` for unique fields:
   ```python
   name = factory.Sequence(lambda n: f"template_{n}")
   ```

3. Use `factory.SubFactory(UserFactory)` for FK relationships.

4. Use `factory.LazyFunction` for dynamic defaults:
   ```python
   expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
   ```

5. Create variant factories via inheritance:
   ```python
   class FailedEmailLogFactory(EmailLogFactory):
       status = EmailLog.Status.FAILED
   ```

### auto_now_add Workaround

Fields with `auto_now_add=True` (like `created_at` on TimeStampedModel) ignore factory kwargs. To set them for testing:

```python
log = EmailLogFactory()
EmailLog.objects.filter(pk=log.pk).update(created_at=now - timedelta(days=91))
```

## Test Patterns By Layer

### Models

Test creation, constraints, properties, and `__str__`:

```python
def test_unique_together_constraint(self, user):
    NotificationPreferenceFactory(user=user, notification_type="new_login")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            NotificationPreferenceFactory(user=user, notification_type="new_login")

def test_ordering(self):
    assert NotificationLog._meta.ordering == ['-created_at']

def test_user_on_delete_set_null(self, user):
    log = NotificationLogFactory(user=user)
    user.delete()
    log.refresh_from_db()
    assert log.user is None
```

### Services

Mock at service boundaries (email, notifications, audit, external APIs):

```python
@patch("apps.notifications.tasks.dispatch_notification_task.delay")
@patch("apps.core.observability.audit.service.AuditService.log")
def test_send_creates_log_with_pending_status(self, mock_audit, mock_dispatch, user):
    log = NotificationService.send(
        user=user,
        notification_type="welcome",
        context={},
    )
    assert log.status == NotificationLog.Status.PENDING
    mock_dispatch.assert_called_once_with(str(log.id))
```

### Selectors

Test with real DB data, no mocking:

```python
def test_get_by_email_respects_limit(self, user):
    for _ in range(5):
        EmailLogFactory(to_email="user@example.com")
    result = EmailLogSelector.get_by_email("user@example.com", limit=3)
    assert len(result) == 3
```

### Views

Test auth (401) -> authz (403) -> validation (400) -> happy path -> error cases:

```python
def test_unauthenticated_returns_401(self, api_client, some_url):
    response = api_client.get(some_url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_authenticated_returns_200(self, authenticated_client, some_url):
    response = authenticated_client.get(some_url)
    assert response.status_code == status.HTTP_200_OK
```

### Tasks

Call directly (not via `.delay()`). Test settings use `CELERY_TASK_ALWAYS_EAGER=True`:

```python
@patch("apps.email.services.email_service.EmailService._send_now")
def test_send_email_task_calls_send_now(self, mock_send_now):
    log = EmailLogFactory(status=EmailLog.Status.PENDING)
    send_email_task(str(log.id))
    mock_send_now.assert_called_once()
```

## Assert Patterns

### Status Codes
```python
assert response.status_code == status.HTTP_200_OK
assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

### Exceptions
```python
with pytest.raises(NotFound):
    SomeService.get(id="nonexistent")

with pytest.raises(ValidationError, match="Missing required context"):
    SomeService.validate(context={})
```

### DB State
```python
log.refresh_from_db()
assert log.status == "sent"
assert not SomeModel.objects.filter(pk=deleted_id).exists()
```

### Mocks
```python
mock_service.assert_called_once()
mock_service.assert_called_once_with(str(log.id))
mock_service.assert_not_called()
```

## Mocking Rules

1. **Patch at the import path**, not the definition path:
   ```python
   # If notification_service.py imports: from apps.notifications.tasks import dispatch_notification_task
   @patch("apps.notifications.tasks.dispatch_notification_task.delay")
   ```

2. **Mock at service boundaries only**: external APIs, email sending, notification dispatch, audit logging. Never mock internal helpers.

3. **AuditService.log** is always mocked in service tests (it writes to DB):
   ```python
   @patch("apps.core.observability.audit.service.AuditService.log")
   ```

4. **DummyCache workaround**: Test settings use DummyCache. For cache-dependent tests, use:
   ```python
   @pytest.fixture(autouse=True)
   def _use_locmem_cache(self, settings):
       settings.CACHES = {
           "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
       }
   ```

5. **`@override_settings` on pytest classes**: Use `settings` fixture instead. `@override_settings` only works on Django `SimpleTestCase` subclasses:
   ```python
   # DON'T do this on pytest classes:
   @override_settings(CACHES=SOME_CONFIG)
   class TestSomething:  # Will raise ValueError

   # DO this instead:
   class TestSomething:
       @pytest.fixture(autouse=True)
       def _setup_settings(self, settings):
           settings.CACHES = SOME_CONFIG
   ```

## Security Test Requirements

These tests must exist and must never be deleted:

| Test | File | What It Verifies |
|------|------|-----------------|
| Login error consistency | auth/test_services.py | Wrong email and wrong password return same error message |
| Password reset 200 always | auth/test_views.py | Password reset returns 200 regardless of email existence |
| Resend verification 200 always | auth/test_views.py | Resend returns 200 regardless of email existence |
| Refresh token reuse detection | auth/test_services.py | Reused refresh token triggers logout_all |
| JTI blacklist enforcement | auth/test_authentication.py | Blacklisted JTI is rejected |
| Password change requires current | auth/test_views.py | Must provide correct current password |
| Inactive account denied | auth/test_services.py | Inactive account cannot login |

## Markers

```ini
# pytest.ini
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests that test cross-boundary behavior
    celery: marks tests that exercise Celery tasks
```

Usage:
```python
@pytest.mark.slow
def test_send_bulk_1000_users(self):
    ...
```

Run excluding slow: `pytest -m "not slow"`

## Coverage Requirements

| App | Minimum |
|-----|---------|
| core | 85% |
| auth | 85% |
| email | 80% |
| notifications | 80% |
| users | 92% |
| rbac | 93% |
| organization | 89% |
| **Overall** | **80%** |

Run coverage: `make test-cov`

Configuration: `backend/.coveragerc`
