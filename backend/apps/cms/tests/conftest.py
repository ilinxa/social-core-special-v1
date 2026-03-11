# apps/cms/tests/conftest.py
import pytest
from rest_framework.test import APIClient
from apps.cms.tests.factories import (
    SiteFactory, PageFactory, SectionTemplateFactory, BlockTemplateFactory,
    PageSectionPlacementFactory, SectionBlockPlacementFactory,
    MediaFileFactory,
)
from apps.users.tests.factories import UserFactory
from apps.organization.tests.factories import PlatformAccountFactory
from apps.core.constants import OwnerType, AccountType
from apps.rbac.services import RBACService
from apps.rbac.selectors import RoleSelector


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def platform_account(db):
    """Get or create the singleton PlatformAccount."""
    from apps.organization.platform.models import PlatformAccount
    platform = PlatformAccount.objects.first()
    if platform:
        return platform
    return PlatformAccountFactory()


@pytest.fixture
def platform_with_rbac(db, user, platform_account):
    """Platform account with RBAC initialized (roles + owner membership)."""
    RBACService.initialize_platform_account(platform_id=platform_account.id)
    owner_role = RoleSelector.get_owner_role(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
    )
    RBACService.create_membership(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
        user=user,
        role_id=owner_role.id,
        created_by=user,
    )
    return platform_account


@pytest.fixture
def actor_context(user, platform_with_rbac):
    """Build ActorContext for the platform owner user."""
    from apps.rbac.selectors import MembershipSelector
    membership = MembershipSelector.get_active_membership_for_user_account(
        user=user,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
    )
    return RBACService.build_actor_context(membership=membership)


@pytest.fixture
def site(db, user, platform_with_rbac):
    """Create a CMS site owned by the platform."""
    return SiteFactory(
        owner_type=OwnerType.PLATFORM,
        owner_id=platform_with_rbac.id,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def page(db, site):
    """Create a draft page in the test site."""
    return PageFactory(site=site, created_by=site.created_by, updated_by=site.created_by)


@pytest.fixture
def section_template(db, user):
    return SectionTemplateFactory(created_by=user, updated_by=user)


@pytest.fixture
def block_template(db, user):
    return BlockTemplateFactory(created_by=user, updated_by=user)


@pytest.fixture
def section_placement(db, page, section_template):
    return PageSectionPlacementFactory(page=page, template=section_template)


@pytest.fixture
def block_placement(db, section_placement, block_template, user):
    return SectionBlockPlacementFactory(
        section_placement=section_placement,
        template=block_template,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def published_page(db, site, section_template, block_template, user):
    """Create a fully published page with sections and blocks."""
    from apps.cms.constants import PageStatus, BlockPlacementStatus
    page = PageFactory(
        site=site,
        status=PageStatus.PUBLISHED,
        created_by=user,
        updated_by=user,
    )
    sp = PageSectionPlacementFactory(page=page, template=section_template)
    SectionBlockPlacementFactory(
        section_placement=sp,
        template=block_template,
        draft_content={"title": "Published Title"},
        published_content={"title": "Published Title"},
        status=BlockPlacementStatus.PUBLISHED,
        created_by=user,
        updated_by=user,
    )
    return page


@pytest.fixture
def media_file(db, user, platform_with_rbac):
    return MediaFileFactory(
        owner_type=OwnerType.PLATFORM,
        owner_id=platform_with_rbac.id,
        created_by=user,
        updated_by=user,
    )
