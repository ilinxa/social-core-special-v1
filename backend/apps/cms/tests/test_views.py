# apps/cms/tests/test_views.py
"""
CMS API view tests.

Tests cover admin endpoints (authenticated + RBAC) and public endpoints (API key).
"""

import pytest
from rest_framework.test import APIClient

from apps.cms.constants import BlockPlacementStatus, PageStatus
from apps.cms.models import CMSApiKey
from apps.cms.tests.factories import (
    BlockTemplateFactory,
    CMSApiKeyFactory,
    ContentVersionFactory,
    PageFactory,
    PageSectionPlacementFactory,
    SectionBlockPlacementFactory,
    SectionTemplateFactory,
    SiteFactory,
)
from apps.core.constants import OwnerType

# =========================================================================
# URL helpers
# =========================================================================

ADMIN_PREFIX = "/api/v1/cms/admin"
PUBLIC_PREFIX = "/api/v1/cms/public"


def admin_sites_url():
    return f"{ADMIN_PREFIX}/sites/"


def admin_site_detail_url(slug):
    return f"{ADMIN_PREFIX}/sites/{slug}/"


def admin_pages_url():
    return f"{ADMIN_PREFIX}/pages/"


def admin_page_detail_url(slug):
    return f"{ADMIN_PREFIX}/pages/{slug}/"


def admin_page_publish_url(slug):
    return f"{ADMIN_PREFIX}/pages/{slug}/publish/"


def admin_page_unpublish_url(slug):
    return f"{ADMIN_PREFIX}/pages/{slug}/unpublish/"


def admin_page_export_url(slug):
    return f"{ADMIN_PREFIX}/pages/{slug}/export/"


def admin_section_templates_url():
    return f"{ADMIN_PREFIX}/templates/sections/"


def admin_block_templates_url():
    return f"{ADMIN_PREFIX}/templates/blocks/"


def admin_block_placement_url(uuid):
    return f"{ADMIN_PREFIX}/block-placements/{uuid}/"


def admin_block_placement_history_url(uuid):
    return f"{ADMIN_PREFIX}/block-placements/{uuid}/history/"


def admin_block_placement_rollback_url(uuid, version_number):
    return f"{ADMIN_PREFIX}/block-placements/{uuid}/rollback/{version_number}/"


def admin_media_files_url():
    return f"{ADMIN_PREFIX}/media/files/"


def admin_media_file_detail_url(uuid):
    return f"{ADMIN_PREFIX}/media/files/{uuid}/"


def admin_api_keys_url():
    return f"{ADMIN_PREFIX}/api-keys/"


def admin_api_key_detail_url(uuid):
    return f"{ADMIN_PREFIX}/api-keys/{uuid}/"


def public_site_url(slug):
    return f"{PUBLIC_PREFIX}/sites/{slug}/"


def public_page_url(slug):
    return f"{PUBLIC_PREFIX}/pages/{slug}/"


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def api_key_and_plaintext(actor_context, site):
    """Create an API key and return (api_key, plaintext)."""
    from apps.cms.services import CMSApiKeyService

    return CMSApiKeyService.create_api_key(
        actor_context=actor_context,
        site_id=site.id,
        name="Test Key",
    )


# =========================================================================
# ADMIN — Sites
# =========================================================================


@pytest.mark.django_db
class TestAdminSiteListCreateView:
    def test_list_sites_authenticated(self, authenticated_client, site):
        response = authenticated_client.get(admin_sites_url())
        assert response.status_code == 200

    def test_list_sites_unauthenticated(self, api_client):
        response = api_client.get(admin_sites_url())
        assert response.status_code == 401

    def test_create_site(self, authenticated_client, platform_with_rbac):
        data = {
            "name": "New Site",
            "slug": "new-site",
        }
        response = authenticated_client.post(admin_sites_url(), data, format="json")
        assert response.status_code == 201
        assert response.data["slug"] == "new-site"

    def test_create_site_duplicate_slug(self, authenticated_client, site):
        data = {
            "name": "Another",
            "slug": site.slug,
        }
        response = authenticated_client.post(admin_sites_url(), data, format="json")
        assert response.status_code == 409


@pytest.mark.django_db
class TestAdminSiteDetailView:
    def test_get_site(self, authenticated_client, site):
        response = authenticated_client.get(admin_site_detail_url(site.slug))
        assert response.status_code == 200
        assert response.data["slug"] == site.slug

    def test_update_site(self, authenticated_client, site):
        data = {"name": "Updated Name"}
        response = authenticated_client.patch(
            admin_site_detail_url(site.slug), data, format="json"
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated Name"

    def test_delete_site(self, authenticated_client, site):
        response = authenticated_client.delete(admin_site_detail_url(site.slug))
        assert response.status_code == 204

    def test_get_nonexistent_site(self, authenticated_client, platform_with_rbac):
        response = authenticated_client.get(admin_site_detail_url("no-such-site"))
        assert response.status_code == 404


# =========================================================================
# ADMIN — Pages
# =========================================================================


@pytest.mark.django_db
class TestAdminPageListCreateView:
    def test_list_pages(self, authenticated_client, page):
        response = authenticated_client.get(admin_pages_url(), {"site": page.site.slug})
        assert response.status_code == 200

    def test_create_page(self, authenticated_client, site):
        data = {
            "site_id": str(site.id),
            "title": "New Page",
            "slug": "new-page",
            "path": "/new-page",
            "page_type": "content",
            "order": 0,
        }
        response = authenticated_client.post(admin_pages_url(), data, format="json")
        assert response.status_code == 201
        assert response.data["slug"] == "new-page"

    def test_create_page_duplicate_slug(self, authenticated_client, page):
        data = {
            "site_id": str(page.site_id),
            "title": "Dup",
            "slug": page.slug,
            "path": "/dup",
            "page_type": "content",
            "order": 999,
        }
        response = authenticated_client.post(admin_pages_url(), data, format="json")
        assert response.status_code == 409


@pytest.mark.django_db
class TestAdminPagePublishView:
    def test_publish_page_success(self, authenticated_client, page, block_placement):
        block_placement.draft_content = {"title": "Hello", "body": "World"}
        block_placement.save()

        response = authenticated_client.post(
            admin_page_publish_url(page.slug),
            {"site": page.site.slug},
            format="json",
        )
        # The publish URL requires site as query param
        response = authenticated_client.post(
            admin_page_publish_url(page.slug) + f"?site={page.site.slug}",
        )
        assert response.status_code == 200
        assert response.data["status"] == PageStatus.PUBLISHED

    def test_publish_page_validation_failure(
        self, authenticated_client, page, block_placement
    ):
        block_placement.draft_content = {"title": "", "body": ""}
        block_placement.is_visible = True
        block_placement.save()

        response = authenticated_client.post(
            admin_page_publish_url(page.slug) + f"?site={page.site.slug}",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestAdminPageUnpublishView:
    def test_unpublish_published_page(self, authenticated_client, published_page):
        response = authenticated_client.post(
            admin_page_unpublish_url(published_page.slug)
            + f"?site={published_page.site.slug}",
        )
        assert response.status_code == 200
        assert response.data["status"] == PageStatus.DRAFT

    def test_unpublish_draft_page_fails(self, authenticated_client, page):
        response = authenticated_client.post(
            admin_page_unpublish_url(page.slug) + f"?site={page.site.slug}",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestAdminPageExportView:
    def test_export_page(self, authenticated_client, page, block_placement):
        response = authenticated_client.post(
            admin_page_export_url(page.slug) + f"?site={page.site.slug}",
        )
        assert response.status_code == 200
        assert response.data["export_version"] == "3.1"
        assert "page" in response.data


# =========================================================================
# ADMIN — Templates
# =========================================================================


@pytest.mark.django_db
class TestAdminSectionTemplateListCreateView:
    def test_list_section_templates(self, authenticated_client, section_template):
        response = authenticated_client.get(admin_section_templates_url())
        assert response.status_code == 200

    def test_create_section_template(self, authenticated_client, platform_with_rbac):
        data = {
            "name": "hero",
            "display_name": "Hero Section",
            "slug": "hero-section",
            "section_type": "hero",
        }
        response = authenticated_client.post(
            admin_section_templates_url(), data, format="json"
        )
        assert response.status_code == 201
        assert response.data["slug"] == "hero-section"


@pytest.mark.django_db
class TestAdminBlockTemplateListCreateView:
    def test_list_block_templates(self, authenticated_client, block_template):
        response = authenticated_client.get(admin_block_templates_url())
        assert response.status_code == 200

    def test_create_block_template(self, authenticated_client, platform_with_rbac):
        data = {
            "name": "heading_block",
            "display_name": "Heading",
            "slug": "heading-block",
            "block_type": "heading",
            "schema": {
                "fields": [
                    {"key": "title", "type": "text", "required": True},
                ]
            },
        }
        response = authenticated_client.post(
            admin_block_templates_url(), data, format="json"
        )
        assert response.status_code == 201
        assert response.data["schema_version"] == 1

    def test_create_block_template_invalid_schema(
        self, authenticated_client, platform_with_rbac
    ):
        data = {
            "name": "bad",
            "display_name": "Bad",
            "slug": "bad-block",
            "block_type": "bad",
            "schema": {},
        }
        response = authenticated_client.post(
            admin_block_templates_url(), data, format="json"
        )
        assert response.status_code == 400


# =========================================================================
# ADMIN — Block Placements (Content)
# =========================================================================


@pytest.mark.django_db
class TestAdminBlockPlacementDetailView:
    def test_get_block_placement(self, authenticated_client, block_placement):
        response = authenticated_client.get(
            admin_block_placement_url(block_placement.id)
        )
        assert response.status_code == 200
        assert response.data["id"] == str(block_placement.id)

    def test_update_draft_content(self, authenticated_client, block_placement):
        data = {"draft_content": {"title": "Updated via API", "body": "Content"}}
        response = authenticated_client.patch(
            admin_block_placement_url(block_placement.id), data, format="json"
        )
        assert response.status_code == 200
        assert response.data["draft_content"]["title"] == "Updated via API"


@pytest.mark.django_db
class TestAdminBlockPlacementHistoryView:
    def test_list_versions(self, authenticated_client, block_placement, user):
        ContentVersionFactory(
            block_placement=block_placement,
            version_number=1,
            created_by=user,
        )
        response = authenticated_client.get(
            admin_block_placement_history_url(block_placement.id)
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminBlockPlacementRollbackView:
    def test_rollback_content(self, authenticated_client, block_placement, user):
        ContentVersionFactory(
            block_placement=block_placement,
            content_snapshot={"title": "Version 1"},
            version_number=1,
            created_by=user,
        )
        response = authenticated_client.post(
            admin_block_placement_rollback_url(block_placement.id, 1)
        )
        assert response.status_code == 200
        assert response.data["draft_content"] == {"title": "Version 1"}


# =========================================================================
# ADMIN — API Keys
# =========================================================================


@pytest.mark.django_db
class TestAdminApiKeyListCreateView:
    def test_create_api_key(self, authenticated_client, site):
        data = {
            "site_id": str(site.id),
            "name": "Test Key",
        }
        response = authenticated_client.post(admin_api_keys_url(), data, format="json")
        assert response.status_code == 201
        assert "key" in response.data
        assert response.data["key"].startswith("cmsk_")

    def test_list_api_keys(self, authenticated_client, api_key_and_plaintext, site):
        response = authenticated_client.get(admin_api_keys_url() + f"?site={site.id}")
        assert response.status_code == 200


@pytest.mark.django_db
class TestAdminApiKeyDetailView:
    def test_revoke_api_key(self, authenticated_client, api_key_and_plaintext):
        api_key, _ = api_key_and_plaintext
        response = authenticated_client.delete(admin_api_key_detail_url(api_key.id))
        assert response.status_code == 204


# =========================================================================
# PUBLIC — API Key Authentication
# =========================================================================


@pytest.mark.django_db
class TestPublicSiteView:
    def test_public_site_with_valid_key(self, api_client, site, api_key_and_plaintext):
        _, plaintext = api_key_and_plaintext
        response = api_client.get(
            public_site_url(site.slug),
            HTTP_X_CMS_API_KEY=plaintext,
        )
        assert response.status_code == 200
        assert response.data["slug"] == site.slug

    def test_public_site_without_key(self, api_client, site):
        response = api_client.get(public_site_url(site.slug))
        assert response.status_code == 401

    def test_public_site_with_invalid_key(self, api_client, site):
        response = api_client.get(
            public_site_url(site.slug),
            HTTP_X_CMS_API_KEY="cmsk_invalid_key_value",
        )
        assert response.status_code == 401

    def test_public_site_wrong_slug(self, api_client, api_key_and_plaintext):
        _, plaintext = api_key_and_plaintext
        response = api_client.get(
            public_site_url("wrong-slug"),
            HTTP_X_CMS_API_KEY=plaintext,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestPublicPageView:
    def test_public_page_published(
        self, api_client, published_page, api_key_and_plaintext
    ):
        _, plaintext = api_key_and_plaintext
        response = api_client.get(
            public_page_url(published_page.slug),
            HTTP_X_CMS_API_KEY=plaintext,
        )
        assert response.status_code == 200

    def test_public_page_draft_not_visible(
        self, api_client, page, api_key_and_plaintext
    ):
        _, plaintext = api_key_and_plaintext
        response = api_client.get(
            public_page_url(page.slug),
            HTTP_X_CMS_API_KEY=plaintext,
        )
        assert response.status_code == 404

    def test_public_page_without_key(self, api_client, published_page):
        response = api_client.get(public_page_url(published_page.slug))
        assert response.status_code == 401

    def test_public_page_full_depth(
        self, api_client, published_page, api_key_and_plaintext
    ):
        _, plaintext = api_key_and_plaintext
        response = api_client.get(
            public_page_url(published_page.slug) + "?depth=full",
            HTTP_X_CMS_API_KEY=plaintext,
        )
        assert response.status_code == 200
        assert "section_placements" in response.data
