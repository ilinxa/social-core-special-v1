# apps/explore/tests/conftest.py
import pytest

from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    """Verified user override — explore tests assume ``is_verified=True``."""
    return UserFactory(is_verified=True)


@pytest.fixture
def authenticated_client(api_client, user):
    """Override hoisted ``authenticated_client`` with real JWT login.

    Explore's auth tests exercise the full ``AuthService.login`` path; the
    default ``force_authenticate``-based fixture bypasses what we want to cover.
    """
    from apps.auth.services import AuthService

    tokens = AuthService.login(email=user.email, password="testpass123")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return api_client
