# apps/network/tests/conftest.py
import uuid

import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def user_b(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def user_c(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def business(db):
    """Create a business with profile for testing."""
    from apps.core.constants import BusinessStatus
    from apps.organization.tests.factories import (
        BusinessAccountFactory,
        BusinessProfileFactory,
    )
    from apps.rbac.services import RBACService

    biz = BusinessAccountFactory(status=BusinessStatus.ACTIVE)
    BusinessProfileFactory(business=biz, is_public=True)
    RBACService.initialize_business_account(business_id=biz.id, owner=biz.created_by)
    return biz


@pytest.fixture
def private_business(db):
    """Create a private business for testing."""
    from apps.core.constants import BusinessStatus
    from apps.organization.tests.factories import (
        BusinessAccountFactory,
        BusinessProfileFactory,
    )
    from apps.rbac.services import RBACService

    biz = BusinessAccountFactory(status=BusinessStatus.ACTIVE)
    BusinessProfileFactory(business=biz, is_public=False)
    RBACService.initialize_business_account(business_id=biz.id, owner=biz.created_by)
    return biz


@pytest.fixture
def business_id(business):
    return business.id


@pytest.fixture
def immediate_on_commit(monkeypatch):
    """Execute transaction.on_commit() callbacks immediately.

    Needed because pytest-django wraps tests in a transaction that never
    commits, so on_commit callbacks registered inside nested atomic blocks
    are deferred indefinitely. This fixture makes them fire synchronously.
    """
    monkeypatch.setattr(
        "django.db.transaction.on_commit",
        lambda func, using=None, robust=False: func(),
    )


@pytest.fixture
def platform(db):
    """Get or create the platform account."""
    from apps.organization.platform.selectors import PlatformAccountSelector

    try:
        return PlatformAccountSelector.get_platform()
    except Exception:
        from apps.organization.tests.factories import PlatformAccountFactory

        return PlatformAccountFactory()
