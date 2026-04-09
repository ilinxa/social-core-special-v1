# apps/cms/tests/test_business_views.py
"""
Tests for business-scoped CMS API views.
"""

import pytest
from rest_framework.test import APIClient

from apps.cms.constants import TemplateOrgType
from apps.cms.tests.factories import (
    BlockTemplateFactory,
    SectionTemplateFactory,
    SiteFactory,
)
from apps.core.constants import OwnerType


@pytest.fixture
def authenticated_client(business_user):
    client = APIClient()
    client.force_authenticate(user=business_user)
    return client


def _biz_url(business_account, path):
    return f"/api/v1/cms/business/{business_account.slug}/{path}"


# =============================================================================
# Feature Gate & CMS Flag Tests
# =============================================================================


@pytest.mark.django_db
class TestBusinessCMSGates:
    def test_requires_feature_gate(
        self, authenticated_client, business_account, feature_config_override
    ):
        """403 when business.cms.enabled=False in deployment config."""
        feature_config_override({"business": {"cms": {"enabled": False}}})
        response = authenticated_client.get(
            _biz_url(business_account, "catalog/sections/")
        )
        assert response.status_code == 403

    def test_requires_cms_enabled_on_business(
        self, authenticated_client, business_account
    ):
        """403 when business.cms_enabled=False."""
        business_account.cms_enabled = False
        business_account.save(update_fields=["cms_enabled"])
        response = authenticated_client.get(
            _biz_url(business_account, "catalog/sections/")
        )
        assert response.status_code == 403

    def test_requires_authentication(self, business_account):
        """401 when not authenticated."""
        client = APIClient()
        response = client.get(_biz_url(business_account, "catalog/sections/"))
        assert response.status_code in (401, 403)


# =============================================================================
# Template Catalog Tests
# =============================================================================


@pytest.mark.django_db
class TestBusinessCatalog:
    def test_catalog_sections_lists_eligible(
        self, authenticated_client, business_account
    ):
        SectionTemplateFactory(org_type=TemplateOrgType.ALL)
        SectionTemplateFactory(org_type=TemplateOrgType.BUSINESS)
        SectionTemplateFactory(org_type=TemplateOrgType.PLATFORM)  # not eligible

        response = authenticated_client.get(
            _biz_url(business_account, "catalog/sections/")
        )
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_catalog_blocks_lists_eligible(
        self, authenticated_client, business_account
    ):
        BlockTemplateFactory(org_type=TemplateOrgType.ALL)
        BlockTemplateFactory(org_type=TemplateOrgType.SYSTEM)  # not eligible

        response = authenticated_client.get(
            _biz_url(business_account, "catalog/blocks/")
        )
        assert response.status_code == 200
        assert response.data["count"] == 1


# =============================================================================
# Template Library Tests
# =============================================================================


@pytest.mark.django_db
class TestBusinessLibrary:
    def test_library_sections_list(
        self, authenticated_client, business_account, activated_section_template
    ):
        response = authenticated_client.get(
            _biz_url(business_account, "library/sections/")
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_library_activate_section(
        self, authenticated_client, business_account, business_section_template
    ):
        response = authenticated_client.post(
            _biz_url(business_account, "library/sections/"),
            {"template_id": str(business_section_template.id)},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["template"]["id"] == str(business_section_template.id)

    def test_library_deactivate_section(
        self, authenticated_client, business_account, activated_section_template
    ):
        response = authenticated_client.delete(
            _biz_url(
                business_account,
                f"library/sections/{activated_section_template.id}/",
            )
        )
        assert response.status_code == 204

    def test_library_blocks_list(
        self, authenticated_client, business_account, activated_block_template
    ):
        response = authenticated_client.get(
            _biz_url(business_account, "library/blocks/")
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_library_activate_block(
        self, authenticated_client, business_account, business_block_template
    ):
        response = authenticated_client.post(
            _biz_url(business_account, "library/blocks/"),
            {"template_id": str(business_block_template.id)},
            format="json",
        )
        assert response.status_code == 201


# =============================================================================
# Business Sites Tests
# =============================================================================


@pytest.mark.django_db
class TestBusinessSites:
    def test_list_sites(self, authenticated_client, business_account, business_user):
        SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        response = authenticated_client.get(_biz_url(business_account, "sites/"))
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_create_site(self, authenticated_client, business_account):
        response = authenticated_client.post(
            _biz_url(business_account, "sites/"),
            {"name": "Business Site", "slug": "biz-site"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["slug"] == "biz-site"
        assert response.data["owner_type"] == "business"

    def test_create_site_duplicate_slug(
        self, authenticated_client, business_account, business_user
    ):
        SiteFactory(
            slug="dup-slug",
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        response = authenticated_client.post(
            _biz_url(business_account, "sites/"),
            {"name": "Dup", "slug": "dup-slug"},
            format="json",
        )
        assert response.status_code == 409

    def test_sites_scoped_to_business(
        self, authenticated_client, business_account, business_user
    ):
        """Business sites list only returns its own sites."""
        SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        SiteFactory(owner_type=OwnerType.PLATFORM)  # different org

        response = authenticated_client.get(_biz_url(business_account, "sites/"))
        assert response.status_code == 200
        assert response.data["count"] == 1


# =============================================================================
# Platform Management Tests
# =============================================================================


@pytest.mark.django_db
class TestPlatformBusinessCMSManagement:
    @pytest.fixture
    def platform_client(self, user, platform_with_rbac):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_list_businesses_cms_status(self, platform_client, business_account):
        response = platform_client.get("/api/v1/cms/admin/businesses/")
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) >= 1
        biz = next(r for r in results if r["id"] == str(business_account.id))
        assert biz["cms_enabled"] is True

    def test_toggle_business_cms(self, platform_client, business_account):
        response = platform_client.patch(
            f"/api/v1/cms/admin/businesses/{business_account.id}/",
            {"cms_enabled": False},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["cms_enabled"] is False
        business_account.refresh_from_db()
        assert business_account.cms_enabled is False

    def test_view_business_activations(
        self, platform_client, business_account, activated_section_template
    ):
        response = platform_client.get(
            f"/api/v1/cms/admin/businesses/{business_account.id}/activations/"
        )
        assert response.status_code == 200
        assert len(response.data["section_templates"]) == 1
        assert len(response.data["block_templates"]) == 0


# =============================================================================
# Business Page & Content Tests
# =============================================================================


@pytest.mark.django_db
class TestBusinessPages:
    def test_create_page(self, authenticated_client, business_account, business_user):
        site = SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        response = authenticated_client.post(
            _biz_url(business_account, "pages/"),
            {
                "site_id": str(site.id),
                "title": "Home",
                "slug": "home",
                "path": "/home",
                "page_type": "landing",
                "order": 0,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["slug"] == "home"

    def test_publish_page(
        self,
        authenticated_client,
        business_account,
        business_user,
        activated_block_template,
        activated_section_template,
    ):
        from apps.cms.constants import BlockPlacementStatus, PageStatus
        from apps.cms.tests.factories import (
            PageFactory,
            PageSectionPlacementFactory,
            SectionBlockPlacementFactory,
        )

        site = SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        page = PageFactory(
            site=site, created_by=business_user, updated_by=business_user
        )
        sp = PageSectionPlacementFactory(
            page=page, template=activated_section_template.template
        )
        SectionBlockPlacementFactory(
            section_placement=sp,
            template=activated_block_template.template,
            draft_content={"title": "Hello", "body": "World"},
            created_by=business_user,
            updated_by=business_user,
        )
        response = authenticated_client.post(
            _biz_url(business_account, f"pages/{page.slug}/publish/")
            + f"?site={site.slug}"
        )
        assert response.status_code == 200
        assert response.data["status"] == PageStatus.PUBLISHED
