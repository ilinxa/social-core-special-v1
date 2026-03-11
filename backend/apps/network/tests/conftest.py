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
    from apps.organization.tests.factories import (
        BusinessAccountFactory,
        BusinessProfileFactory,
    )
    from apps.rbac.services import RBACService
    from apps.core.constants import BusinessStatus

    biz = BusinessAccountFactory(status=BusinessStatus.ACTIVE)
    BusinessProfileFactory(business=biz, is_public=True)
    RBACService.initialize_business_account(business_id=biz.id, owner=biz.created_by)
    return biz


@pytest.fixture
def private_business(db):
    """Create a private business for testing."""
    from apps.organization.tests.factories import (
        BusinessAccountFactory,
        BusinessProfileFactory,
    )
    from apps.rbac.services import RBACService
    from apps.core.constants import BusinessStatus

    biz = BusinessAccountFactory(status=BusinessStatus.ACTIVE)
    BusinessProfileFactory(business=biz, is_public=False)
    RBACService.initialize_business_account(business_id=biz.id, owner=biz.created_by)
    return biz


@pytest.fixture
def business_id(business):
    return business.id


@pytest.fixture
def platform(db):
    """Get or create the platform account."""
    from apps.organization.platform.selectors import PlatformAccountSelector
    try:
        return PlatformAccountSelector.get_platform()
    except Exception:
        from apps.organization.tests.factories import PlatformAccountFactory
        return PlatformAccountFactory()
