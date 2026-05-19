# apps/cms/tests/conftest.py
import pytest

from apps.cms.constants import TemplateOrgType
from apps.cms.models import BlockTemplateActivation, SectionTemplateActivation
from apps.cms.tests.factories import (
    BlockTemplateActivationFactory,
    BlockTemplateFactory,
    MediaFileFactory,
    PageFactory,
    PageSectionPlacementFactory,
    SectionBlockPlacementFactory,
    SectionTemplateActivationFactory,
    SectionTemplateFactory,
    SiteFactory,
)
from apps.core.constants import AccountType, OwnerType
from apps.organization.tests.factories import (
    BusinessAccountFactory,
    PlatformAccountFactory,
)
from apps.rbac.selectors import RoleSelector
from apps.rbac.services import RBACService
from apps.users.tests.factories import UserFactory


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
    return PageFactory(
        site=site, created_by=site.created_by, updated_by=site.created_by
    )


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
    from apps.cms.constants import BlockPlacementStatus, PageStatus

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


# ---------------------------------------------------------------------------
# Business CMS Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def business_user(db):
    """Separate user for business context."""
    return UserFactory()


@pytest.fixture
def business_account(db, business_user):
    """Business with CMS enabled and RBAC initialized."""
    business = BusinessAccountFactory(
        created_by=business_user,
        updated_by=business_user,
    )
    business.cms_enabled = True
    business.save(update_fields=["cms_enabled"])
    RBACService.initialize_business_account(
        business_id=business.id,
        owner=business_user,
    )
    return business


@pytest.fixture
def business_actor_context(business_user, business_account):
    """ActorContext for the business owner."""
    from apps.rbac.selectors import MembershipSelector

    membership = MembershipSelector.get_active_membership_for_user_account(
        user=business_user,
        account_type=AccountType.BUSINESS,
        account_id=business_account.id,
    )
    return RBACService.build_actor_context(membership=membership)


@pytest.fixture
def business_section_template(db, user):
    """Section template eligible for business orgs."""
    return SectionTemplateFactory(
        org_type=TemplateOrgType.ALL,
        is_default=True,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def business_block_template(db, user):
    """Block template eligible for business orgs."""
    return BlockTemplateFactory(
        org_type=TemplateOrgType.ALL,
        is_default=True,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def activated_section_template(
    business_section_template, business_account, business_user
):
    """Section template activated for the business."""
    return SectionTemplateActivationFactory(
        template=business_section_template,
        org_type=OwnerType.BUSINESS,
        org_id=business_account.id,
        activated_by=business_user,
    )


@pytest.fixture
def activated_block_template(business_block_template, business_account, business_user):
    """Block template activated for the business."""
    return BlockTemplateActivationFactory(
        template=business_block_template,
        org_type=OwnerType.BUSINESS,
        org_id=business_account.id,
        activated_by=business_user,
    )
