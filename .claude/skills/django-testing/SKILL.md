---
name: django-testing
description: Implementation guide for writing tests in this Django project using pytest, factory-boy, and pytest-django. Use when writing tests, creating test files, adding test coverage, testing models, testing views, testing serializers, testing permissions, testing API endpoints, creating fixtures, creating factories, writing unit tests, writing integration tests, checking coverage, running tests, or implementing test-driven development (TDD). Covers pytest syntax, factory-boy patterns, DRF testing, mocking, fixtures, conftest setup, and coverage requirements.
---

# Django Testing Implementation

## Quick Start

```python
# apps/your_app/tests/test_views.py
import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestYourViewSet:
    """Tests for YourModel API endpoints."""

    def test_list_requires_auth(self, api_client):
        """Unauthenticated users cannot list items."""
        url = reverse("your-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, authenticated_client, your_factory):
        """Authenticated users can list items."""
        your_factory.create_batch(3)
        url = reverse("your-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 3
```

## Test Structure

```
apps/your_app/
└── tests/
    ├── __init__.py
    ├── conftest.py          # App fixtures
    ├── factories.py         # App factories
    ├── test_models.py
    ├── test_views.py
    ├── test_serializers.py
    └── test_permissions.py
```

## Core Patterns

### 1. Testing Views (DRF ViewSets)

```python
import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestItemViewSet:

    def test_create_item(self, authenticated_client):
        """Can create new item."""
        url = reverse("item-list")
        data = {"title": "Test Item", "content": "Content"}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Test Item"

    def test_update_own_item(self, authenticated_client, item_factory, user):
        """Owner can update their item."""
        item = item_factory(owner=user)
        url = reverse("item-detail", kwargs={"pk": item.pk})
        response = authenticated_client.patch(url, {"title": "Updated"})

        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.title == "Updated"

    def test_cannot_update_others_item(self, authenticated_client, item_factory):
        """Cannot update someone else's item."""
        item = item_factory()  # Different owner
        url = reverse("item-detail", kwargs={"pk": item.pk})
        response = authenticated_client.patch(url, {"title": "Hacked"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
```

### 2. Testing Models

```python
import pytest
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestItemModel:

    def test_create_item(self, user):
        """Can create item with valid data."""
        item = Item.objects.create(
            title="Test",
            owner=user
        )
        assert item.title == "Test"
        assert item.owner == user

    def test_str_representation(self, item_factory):
        """String representation uses title."""
        item = item_factory(title="My Item")
        assert str(item) == "My Item"

    def test_title_required(self, user):
        """Title is required."""
        with pytest.raises(ValidationError):
            item = Item(owner=user)
            item.full_clean()
```

### 3. Testing Serializers

```python
import pytest

@pytest.mark.django_db
class TestItemSerializer:

    def test_valid_data(self):
        """Serializer accepts valid data."""
        data = {"title": "Test", "content": "Content"}
        serializer = ItemSerializer(data=data)
        assert serializer.is_valid()

    def test_missing_required_field(self):
        """Serializer rejects missing title."""
        serializer = ItemSerializer(data={"content": "Content"})
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_read_only_fields_ignored(self, item_factory):
        """Read-only fields cannot be updated."""
        item = item_factory()
        original_created = item.created_at

        serializer = ItemSerializer(
            item,
            data={"title": "Updated", "created_at": "2020-01-01"},
            partial=True
        )
        assert serializer.is_valid()
        serializer.save()

        item.refresh_from_db()
        assert item.created_at == original_created
```

### 4. Factory Pattern

Create factories in `apps/your_app/tests/factories.py`:

```python
import factory
from django.contrib.auth import get_user_model
from apps.your_app.models import Item

User = get_user_model()

class ItemFactory(factory.django.DjangoModelFactory):
    """Factory for Item model."""

    class Meta:
        model = Item

    title = factory.Sequence(lambda n: f"Item {n}")
    content = factory.Faker("paragraph")
    owner = factory.SubFactory("tests.factories.UserFactory")
    is_active = True
```

Register in `apps/your_app/tests/conftest.py`:

```python
import pytest
from .factories import ItemFactory

@pytest.fixture
def item_factory():
    return ItemFactory
```

### 5. Fixtures Pattern

Global fixtures in `backend/tests/conftest.py`:

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()

@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123"
    )

@pytest.fixture
def authenticated_client(api_client, user):
    """API client authenticated as user."""
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def admin_user(db):
    """Create admin user."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123"
    )

@pytest.fixture
def admin_client(api_client, admin_user):
    """API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client
```

### 6. Testing Permissions

```python
import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestItemPermissions:

    def test_list_public_items_no_auth(self, api_client, item_factory):
        """Public items can be listed without auth."""
        item_factory.create_batch(3, is_public=True)
        url = reverse("item-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_requires_auth(self, api_client):
        """Creating items requires authentication."""
        url = reverse("item-list")
        response = api_client.post(url, {"title": "Test"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_delete_any(self, admin_client, item_factory):
        """Admin can delete any item."""
        item = item_factory()
        url = reverse("item-detail", kwargs={"pk": item.pk})
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
```

### 7. Mocking External Services

```python
from unittest.mock import patch, MagicMock
import pytest

@pytest.mark.django_db
class TestNotificationIntegration:

    @patch("apps.notifications.services.NotificationService.send")
    def test_notification_sent_on_create(self, mock_send, authenticated_client):
        """Notification sent when item created."""
        url = reverse("item-list")
        data = {"title": "Test"}
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        mock_send.assert_called_once()
        assert mock_send.call_args[1]["notification_type"] == "item_created"

    @patch("apps.email.services.EmailService.send")
    def test_email_failure_does_not_prevent_creation(self, mock_send, authenticated_client):
        """Item still created even if email fails."""
        mock_send.side_effect = Exception("Email service down")

        url = reverse("item-list")
        response = authenticated_client.post(url, {"title": "Test"})

        # Creation should succeed despite email failure
        assert response.status_code == status.HTTP_201_CREATED
```

### 8. Testing Services

```python
import pytest
from apps.your_app.services import ItemService

@pytest.mark.django_db
class TestItemService:

    def test_create_item(self, user):
        """Service creates item with owner."""
        item = ItemService.create(
            title="Test",
            content="Content",
            owner=user
        )
        assert item.owner == user
        assert item.title == "Test"

    def test_create_with_notification(self, user):
        """Service sends notification on create."""
        with patch("apps.notifications.services.NotificationService.send") as mock:
            item = ItemService.create(title="Test", owner=user)
            mock.assert_called_once()
```

### 9. Testing Async Tasks (Celery)

```python
import pytest
from apps.your_app.tasks import process_item_task

@pytest.mark.django_db
def test_process_item_task(item_factory):
    """Task processes item correctly."""
    item = item_factory(status="pending")

    # Run task synchronously in tests
    result = process_item_task.apply(args=[str(item.id)])

    assert result.successful()
    item.refresh_from_db()
    assert item.status == "processed"
```

### 10. Arrange-Act-Assert Pattern

```python
@pytest.mark.django_db
def test_user_updates_profile(authenticated_client, user):
    # Arrange
    url = reverse("profile-detail", kwargs={"pk": user.profile.pk})
    data = {"display_name": "New Name"}

    # Act
    response = authenticated_client.patch(url, data)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    user.profile.refresh_from_db()
    assert user.profile.display_name == "New Name"
```

## Running Tests

```bash
# All tests
pytest

# Specific app
pytest apps/users/tests/

# Specific file
pytest apps/users/tests/test_views.py

# Specific test
pytest apps/users/tests/test_views.py::TestUserViewSet::test_list_users

# With coverage
pytest --cov=apps --cov-report=term-missing

# Parallel execution
pytest -n auto

# Stop on first failure
pytest -x

# Run last failed
pytest --lf

# Verbose
pytest -v
```

## Coverage Requirements

Maintain **80% minimum coverage**. Check with:

```bash
pytest --cov=apps --cov-report=term-missing --cov-fail-under=80
```

Coverage excludes:
- Migrations
- Admin files
- `__init__.py`
- Test files

## Common Patterns

### Testing with Multiple Users

```python
@pytest.mark.django_db
def test_user_cannot_see_others_private_items(authenticated_client, item_factory, user):
    """Users only see their own private items."""
    # My items
    my_item = item_factory(owner=user, is_public=False)

    # Other's items
    item_factory.create_batch(3, is_public=False)

    url = reverse("item-list")
    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    ids = [item["id"] for item in response.data["results"]]
    assert str(my_item.id) in ids
    assert len(ids) == 1  # Only my item
```

### Testing Pagination

```python
@pytest.mark.django_db
def test_pagination(authenticated_client, item_factory):
    """API returns paginated results."""
    item_factory.create_batch(25)

    url = reverse("item-list")
    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 25
    assert len(response.data["results"]) == 20  # Default page size
    assert response.data["next"] is not None
```

### Testing Filters

```python
@pytest.mark.django_db
def test_filter_by_status(authenticated_client, item_factory):
    """Can filter items by status."""
    item_factory.create_batch(3, status="active")
    item_factory.create_batch(2, status="inactive")

    url = reverse("item-list")
    response = authenticated_client.get(url, {"status": "active"})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 3
```

### Testing Validation

```python
@pytest.mark.django_db
def test_title_too_long_rejected(authenticated_client):
    """Title over max length is rejected."""
    url = reverse("item-list")
    data = {"title": "a" * 201, "content": "Test"}
    response = authenticated_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "title" in response.data
```

### Testing Edge Cases

```python
@pytest.mark.django_db
class TestEdgeCases:

    def test_empty_string_title(self, authenticated_client):
        """Empty title is rejected."""
        url = reverse("item-list")
        response = authenticated_client.post(url, {"title": ""})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_title_allowed(self, authenticated_client, item_factory):
        """Duplicate titles are allowed."""
        item_factory(title="Duplicate")
        url = reverse("item-list")
        response = authenticated_client.post(url, {"title": "Duplicate"})
        assert response.status_code == status.HTTP_201_CREATED

    def test_special_characters_in_title(self, authenticated_client):
        """Special characters are handled."""
        url = reverse("item-list")
        data = {"title": "<script>alert('xss')</script>"}
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
```

## Test Markers

```python
import pytest

@pytest.mark.slow
def test_expensive_operation():
    """Mark slow tests."""
    pass

@pytest.mark.integration
def test_external_api():
    """Mark integration tests."""
    pass

# Run only fast tests
# pytest -m "not slow"
```

## Factory Tips

### SubFactory for ForeignKey

```python
class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    text = factory.Faker("paragraph")
    post = factory.SubFactory(PostFactory)
    author = factory.SubFactory(UserFactory)
```

### Factory with ManyToMany

```python
class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    title = factory.Faker("sentence")

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)
```

Usage:

```python
@pytest.mark.django_db
def test_post_with_tags(post_factory, tag_factory):
    tags = tag_factory.create_batch(3)
    post = post_factory(tags=tags)
    assert post.tags.count() == 3
```

### Factory with Custom Password

```python
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "defaultpass123"
        self.set_password(password)
        if create:
            self.save()
```

Usage:

```python
@pytest.mark.django_db
def test_user_login(api_client, user_factory):
    user = user_factory(password="mypass123")

    url = reverse("auth-login")
    response = api_client.post(url, {
        "email": user.email,
        "password": "mypass123"
    })
    assert response.status_code == status.HTTP_200_OK
```

## Troubleshooting

### Database Not Available

If you see `no such table` errors, ensure `@pytest.mark.django_db` is present:

```python
@pytest.mark.django_db  # Required!
def test_database_access(user):
    assert user.email == "test@example.com"
```

### Factory Not Creating Objects

Ensure factory is called with `.create()` or use as callable:

```python
# Wrong
user = UserFactory  # Returns class, not instance

# Right
user = UserFactory()  # Creates instance
user = UserFactory.create()  # Explicit create
```

### Authenticated Client Not Working

Ensure fixture receives `user` parameter:

```python
@pytest.fixture
def authenticated_client(api_client, user):  # user parameter required
    api_client.force_authenticate(user=user)
    return api_client
```

### Test Isolation Issues

If tests pass individually but fail together, check for:
- Shared mutable state
- Missing database rollback (add `@pytest.mark.django_db`)
- Cached data

## Quick Reference

### Test File Template

```python
import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestYourFeature:
    """Tests for YourFeature."""

    def test_happy_path(self, authenticated_client):
        """Normal case works."""
        # Arrange
        url = reverse("endpoint")
        data = {"field": "value"}

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED

    def test_edge_case(self, authenticated_client):
        """Edge case handled."""
        pass

    def test_error_case(self, authenticated_client):
        """Error case rejected."""
        pass
```

### Factory Template

```python
import factory
from apps.your_app.models import YourModel

class YourModelFactory(factory.django.DjangoModelFactory):
    """Factory for YourModel."""

    class Meta:
        model = YourModel

    name = factory.Sequence(lambda n: f"Name {n}")
    description = factory.Faker("paragraph")
    owner = factory.SubFactory("tests.factories.UserFactory")
    is_active = True
```

### Conftest Template

```python
import pytest
from .factories import YourModelFactory

@pytest.fixture
def your_model_factory():
    return YourModelFactory
```
