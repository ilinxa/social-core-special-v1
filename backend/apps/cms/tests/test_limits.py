# apps/cms/tests/test_limits.py
"""
Tests for VG limit enforcement in CMS business context.
"""

import pytest

from apps.cms.constants import TemplateOrgType
from apps.cms.services import (
    CMSApiKeyService,
    CMSMediaService,
    CMSPageService,
    CMSSiteService,
    CMSTemplateActivationService,
)
from apps.cms.tests.factories import (
    CMSApiKeyFactory,
    MediaFileFactory,
    PageFactory,
    SectionTemplateFactory,
    SiteFactory,
)
from apps.core.constants import OwnerType
from apps.core.exceptions import BusinessRuleViolation, ValidationError


@pytest.mark.django_db
class TestBusinessCMSSiteLimits:
    def test_site_limit_enforced(
        self, business_actor_context, business_account, feature_config_override
    ):
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_sites": 1}}}
        )
        # Create first site (at limit)
        CMSSiteService.create_site(
            actor_context=business_actor_context,
            name="Site 1",
            slug="site-1",
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
        )
        # Second site should fail
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSSiteService.create_site(
                actor_context=business_actor_context,
                name="Site 2",
                slug="site-2",
                owner_type=OwnerType.BUSINESS,
                owner_id=business_account.id,
            )
        assert exc.value.details["rule"] == "cms_max_sites_exceeded"

    def test_site_limit_zero_unlimited(
        self, business_actor_context, business_account, feature_config_override
    ):
        """0 = unlimited (no error)."""
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_sites": 0}}}
        )
        for i in range(3):
            CMSSiteService.create_site(
                actor_context=business_actor_context,
                name=f"Site {i}",
                slug=f"site-{i}",
                owner_type=OwnerType.BUSINESS,
                owner_id=business_account.id,
            )


@pytest.mark.django_db
class TestBusinessCMSPageLimits:
    def test_page_limit_enforced(
        self,
        business_actor_context,
        business_account,
        business_user,
        feature_config_override,
    ):
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_pages_per_site": 1}}}
        )
        site = SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        CMSPageService.create_page(
            actor_context=business_actor_context,
            site_id=site.id,
            title="Page 1",
            slug="page-1",
            path="/page-1",
            page_type="content",
            order=0,
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSPageService.create_page(
                actor_context=business_actor_context,
                site_id=site.id,
                title="Page 2",
                slug="page-2",
                path="/page-2",
                page_type="content",
                order=1,
            )
        assert exc.value.details["rule"] == "cms_max_pages_per_site_exceeded"


@pytest.mark.django_db
class TestBusinessCMSApiKeyLimits:
    def test_api_key_limit_enforced(
        self,
        business_actor_context,
        business_account,
        business_user,
        feature_config_override,
    ):
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_api_keys_per_site": 1}}}
        )
        site = SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        CMSApiKeyService.create_api_key(
            actor_context=business_actor_context,
            site_id=site.id,
            name="Key 1",
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSApiKeyService.create_api_key(
                actor_context=business_actor_context,
                site_id=site.id,
                name="Key 2",
            )
        assert exc.value.details["rule"] == "cms_max_api_keys_per_site_exceeded"


@pytest.mark.django_db
class TestBusinessCMSTemplateActivationLimits:
    def test_block_template_limit_enforced(
        self, business_actor_context, feature_config_override
    ):
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_active_block_templates": 1}}}
        )
        bt1 = SectionTemplateFactory(org_type=TemplateOrgType.ALL)
        bt2 = SectionTemplateFactory(org_type=TemplateOrgType.ALL)

        from apps.cms.tests.factories import BlockTemplateFactory

        bt1 = BlockTemplateFactory(org_type=TemplateOrgType.ALL)
        bt2 = BlockTemplateFactory(org_type=TemplateOrgType.ALL)

        CMSTemplateActivationService.activate_block_template(
            actor_context=business_actor_context,
            template_id=bt1.id,
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSTemplateActivationService.activate_block_template(
                actor_context=business_actor_context,
                template_id=bt2.id,
            )
        assert exc.value.details["rule"] == "max_active_block_templates_exceeded"


@pytest.mark.django_db
class TestPlatformNoBusinessLimits:
    def test_platform_skips_business_limits(
        self, actor_context, platform_with_rbac, feature_config_override
    ):
        """Platform context does not enforce business.cms limits."""
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_sites": 1}}}
        )
        # Platform can create unlimited sites
        for i in range(3):
            CMSSiteService.create_site(
                actor_context=actor_context,
                name=f"Platform Site {i}",
                slug=f"platform-site-{i}",
                owner_type=OwnerType.PLATFORM,
                owner_id=platform_with_rbac.id,
            )
