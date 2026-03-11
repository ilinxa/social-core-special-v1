# apps/explore/tests/conftest.py
import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory, VerifiedUserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def authenticated_client(api_client, user):
    """API client with JWT authentication."""
    from apps.auth.services import AuthService
    tokens = AuthService.login(email=user.email, password="testpass123")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return api_client
