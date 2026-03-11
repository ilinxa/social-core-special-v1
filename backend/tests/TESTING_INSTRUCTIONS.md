# Testing Instructions

This document provides comprehensive guidance for testing in this Django project.

---

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Fixtures and Factories](#fixtures-and-factories)
6. [Coverage Reports](#coverage-reports)
7. [Best Practices](#best-practices)

---

## Overview

This project uses **pytest** with **pytest-django** for testing. We also use:

- **factory-boy**: For creating test data (model factories)
- **pytest-cov**: For code coverage reports

### Why pytest over Django's TestCase?

| Feature | pytest | Django TestCase |
|---------|--------|-----------------|
| Syntax | Simple functions | Class-based |
| Fixtures | Powerful, reusable | Limited |
| Plugins | Extensive ecosystem | Limited |
| Parallelization | Built-in | Requires extra setup |
| Output | Better readability | Basic |

---

## Test Structure

```
backend/
├── tests/                      # Project-wide tests
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   ├── factories.py            # Base factories
│   └── test_integration.py     # Integration tests
│
├── apps/
│   └── your_app/
│       └── tests/              # App-specific tests
│           ├── __init__.py
│           ├── conftest.py     # App-specific fixtures
│           ├── factories.py    # App-specific factories
│           ├── test_models.py
│           ├── test_views.py
│           ├── test_serializers.py
│           └── test_permissions.py
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_integration.py

# Run specific test function
pytest tests/test_integration.py::test_health_check

# Run tests matching a pattern
pytest -k "test_user"

# Run tests in a specific app
pytest apps/users/tests/
```

### With Coverage

```bash
# Run tests with coverage report
pytest --cov=apps --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=apps --cov-report=html
# Open htmlcov/index.html in browser

# Generate XML coverage (for CI)
pytest --cov=apps --cov-report=xml
```

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

### Using Different Databases

```bash
# Use SQLite (fast, local development)
DJANGO_SETTINGS_MODULE=backend_core.settings.local pytest

# Use PostgreSQL (production-like, requires Docker)
DJANGO_SETTINGS_MODULE=backend_core.settings.local_docker pytest
```

---

## Writing Tests

### Basic Test Structure

```python
# tests/test_example.py
import pytest
from django.urls import reverse
from rest_framework import status


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_returns_200(self, api_client):
        """Health check endpoint should return 200 OK."""
        url = reverse("health-check")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_health_check_returns_json(self, api_client):
        """Health check should return JSON response."""
        url = reverse("health-check")
        response = api_client.get(url)
        assert response["Content-Type"] == "application/json"
```

### Testing Views

```python
# apps/users/tests/test_views.py
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestUserViewSet:
    """Tests for User API endpoints."""

    def test_list_users_requires_auth(self, api_client):
        """Unauthenticated users cannot list users."""
        url = reverse("user-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_users_authenticated(self, authenticated_client, user_factory):
        """Authenticated users can list users."""
        # Create some users
        user_factory.create_batch(3)

        url = reverse("user-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 3

    def test_create_user(self, api_client):
        """Can create a new user."""
        url = reverse("user-list")
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123"
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
```

### Testing Models

```python
# apps/users/tests/test_models.py
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model."""

    def test_create_user(self):
        """Can create a regular user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        """Can create a superuser."""
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        assert user.is_staff
        assert user.is_superuser

    def test_user_str(self, user_factory):
        """User string representation."""
        user = user_factory(username="johndoe")
        assert str(user) == "johndoe"
```

### Testing Serializers

```python
# apps/users/tests/test_serializers.py
import pytest
from apps.users.serializers import UserSerializer


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for User serializer."""

    def test_valid_data(self):
        """Serializer accepts valid data."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass123"
        }
        serializer = UserSerializer(data=data)
        assert serializer.is_valid()

    def test_invalid_email(self):
        """Serializer rejects invalid email."""
        data = {
            "username": "testuser",
            "email": "not-an-email",
            "password": "securepass123"
        }
        serializer = UserSerializer(data=data)
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_password_not_in_output(self, user_factory):
        """Password should not be in serialized output."""
        user = user_factory()
        serializer = UserSerializer(user)
        assert "password" not in serializer.data
```

---

## Fixtures and Factories

### Fixtures (conftest.py)

Fixtures are reusable test dependencies. Define them in `conftest.py`:

```python
# tests/conftest.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an API client authenticated as the test user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123"
    )


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client
```

### Factories (factory-boy)

Factories generate test data with realistic values:

```python
# tests/factories.py
import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password after user creation."""
        password = extracted or "defaultpass123"
        self.set_password(password)
        if create:
            self.save()


# Register factory as a fixture in conftest.py
@pytest.fixture
def user_factory():
    """Return UserFactory for creating users in tests."""
    return UserFactory
```

### Using Factories in Tests

```python
# In your test file
@pytest.mark.django_db
class TestSomething:

    def test_with_single_user(self, user_factory):
        """Test with a single user."""
        user = user_factory(username="custom_name")
        assert user.username == "custom_name"

    def test_with_multiple_users(self, user_factory):
        """Test with multiple users."""
        users = user_factory.create_batch(5)
        assert len(users) == 5

    def test_with_custom_attributes(self, user_factory):
        """Test with custom user attributes."""
        admin = user_factory(is_staff=True, is_superuser=True)
        assert admin.is_staff
        assert admin.is_superuser
```

---

## Coverage Reports

### Minimum Coverage Requirements

We recommend maintaining at least **80% code coverage**:

```ini
# In pytest.ini or pyproject.toml
[tool:pytest]
addopts = --cov=apps --cov-fail-under=80
```

### Understanding Coverage Reports

```
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
apps/users/models.py                 25      2    92%   45-46
apps/users/views.py                  50     10    80%   23-25, 67-74
apps/users/serializers.py            30      0   100%
---------------------------------------------------------------
TOTAL                               105     12    89%
```

- **Stmts**: Total statements
- **Miss**: Statements not covered by tests
- **Cover**: Coverage percentage
- **Missing**: Line numbers not covered

### Coverage Configuration

```ini
# .coveragerc or in pyproject.toml
[coverage:run]
source = apps
omit =
    */migrations/*
    */tests/*
    */__init__.py
    */admin.py

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
```

---

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive, indicates what is being tested
def test_user_cannot_access_admin_panel_without_permissions():
    pass

# Bad: Vague, doesn't indicate the test purpose
def test_user():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_user_creation(self, user_factory):
    # Arrange: Set up test data
    data = {"username": "newuser", "email": "new@example.com"}

    # Act: Perform the action being tested
    user = user_factory(**data)

    # Assert: Verify the results
    assert user.username == "newuser"
    assert user.email == "new@example.com"
```

### 3. One Assert Per Test (When Possible)

```python
# Good: Focused tests
def test_user_is_active_by_default(self, user_factory):
    user = user_factory()
    assert user.is_active

def test_user_is_not_staff_by_default(self, user_factory):
    user = user_factory()
    assert not user.is_staff

# Acceptable: Related assertions
def test_user_default_permissions(self, user_factory):
    user = user_factory()
    assert user.is_active
    assert not user.is_staff
    assert not user.is_superuser
```

### 4. Use Markers for Test Categories

```python
import pytest

@pytest.mark.slow
def test_large_data_processing():
    """This test takes a long time."""
    pass

@pytest.mark.integration
def test_external_api_call():
    """This test requires external services."""
    pass

# Run specific categories
# pytest -m "not slow"
# pytest -m integration
```

### 5. Test Edge Cases

```python
@pytest.mark.django_db
class TestUserValidation:

    def test_empty_username_rejected(self):
        """Empty username should be rejected."""
        pass

    def test_very_long_username_rejected(self):
        """Username over 150 chars should be rejected."""
        pass

    def test_special_characters_in_username(self):
        """Special characters should be handled appropriately."""
        pass

    def test_duplicate_email_rejected(self, user_factory):
        """Duplicate email should be rejected."""
        user_factory(email="existing@example.com")
        # Try to create another with same email...
        pass
```

### 6. Mock External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_email_sent_on_registration(self, api_client):
    """Email should be sent when user registers."""
    with patch("apps.users.views.send_mail") as mock_send:
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123"
        }
        api_client.post("/api/v1/users/", data)

        mock_send.assert_called_once()
        assert "new@example.com" in mock_send.call_args[1]["recipient_list"]
```

---

## Quick Reference

### Common pytest Commands

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest -v` | Verbose output |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Run last failed tests |
| `pytest -k "pattern"` | Run tests matching pattern |
| `pytest --cov=apps` | Run with coverage |
| `pytest -n auto` | Run in parallel |

### Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.django_db` | Test requires database |
| `@pytest.mark.slow` | Slow test (custom) |
| `@pytest.mark.integration` | Integration test (custom) |
| `@pytest.mark.skip` | Skip test |
| `@pytest.mark.xfail` | Expected to fail |

### Fixtures Scope

| Scope | Description |
|-------|-------------|
| `function` | New fixture per test (default) |
| `class` | New fixture per test class |
| `module` | New fixture per module |
| `session` | One fixture for entire session |

```python
@pytest.fixture(scope="session")
def expensive_resource():
    """Created once, shared across all tests."""
    return create_expensive_thing()
```
