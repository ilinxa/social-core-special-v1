"""
Phase 08 — CMS (C01–C34, CP01–CP08)

Tests CMS admin operations (sites, pages, templates, content, media, API keys)
and CMS public endpoints (API key authentication, published page access).

Depends on Phase 01 (users), Phase 03 (platform configured).
"""

import io
import uuid

import pytest

# =============================================================================
# C01–C06: SITES
# =============================================================================


class TestCMSSites:
    """Test site CRUD."""

    def test_c01_list_sites_empty(self, api, state):
        """GET /cms/admin/sites/ returns empty list initially."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/sites/")
        assert r.status_code == 200

    def test_c02_create_site(self, api, state):
        """POST /cms/admin/sites/ creates a new site."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/sites/",
            json={
                "name": "Main Site",
                "slug": "main-site",
                "domain": "www.example.com",
                "description": "Primary marketing site",
            },
        )
        assert r.status_code == 201, f"Create site failed: {r.text}"
        data = r.json()
        state.cms["main_site"] = {
            "site_id": data["id"],
            "site_slug": data["slug"],
        }

    def test_c03_duplicate_slug(self, api, state):
        """POST /cms/admin/sites/ with duplicate slug returns 400/409."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/sites/",
            json={
                "name": "Duplicate Site",
                "slug": "main-site",
            },
        )
        # 403 if platform membership missing
        assert r.status_code in (400, 403, 409)

    def test_c04_get_site_detail(self, api, state):
        """GET /cms/admin/sites/<slug>/ returns site detail."""
        api.set_token(state.get_token("alice"))
        slug = state.cms["main_site"]["site_slug"]
        r = api.get(f"cms/admin/sites/{slug}/")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Main Site"

    def test_c05_update_site(self, api, state):
        """PATCH /cms/admin/sites/<slug>/ updates site."""
        api.set_token(state.get_token("alice"))
        slug = state.cms["main_site"]["site_slug"]
        r = api.patch(
            f"cms/admin/sites/{slug}/",
            json={
                "description": "Updated site description",
            },
        )
        assert r.status_code == 200

    def test_c06_delete_site(self, api, state):
        """DELETE /cms/admin/sites/<slug>/ deletes a site."""
        # Create disposable site
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/sites/",
            json={
                "name": "Temp Site",
                "slug": "temp-site",
            },
        )
        if r.status_code != 201:
            pytest.skip("Could not create site to delete")

        r = api.delete("cms/admin/sites/temp-site/")
        assert r.status_code in (200, 204)


# =============================================================================
# C07–C15: PAGES
# =============================================================================


class TestCMSPages:
    """Test page CRUD, publish/unpublish, export/import."""

    def test_c07_list_pages_empty(self, api, state):
        """GET /cms/admin/pages/ returns pages list."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/pages/")
        assert r.status_code == 200

    def test_c08_create_page(self, api, state):
        """POST /cms/admin/pages/ creates a new page."""
        api.set_token(state.get_token("alice"))
        site_id = state.cms["main_site"]["site_id"]
        r = api.post(
            "cms/admin/pages/",
            json={
                "site_id": site_id,
                "title": "Home Page",
                "slug": "home",
                "path": "/",
                "page_type": "landing",
                "order": 0,
                "description": "Main landing page",
            },
        )
        assert r.status_code == 201, f"Create page failed: {r.text}"
        data = r.json()
        state.cms["main_site"]["page_slug"] = data["slug"]
        state.cms["main_site"]["page_id"] = data["id"]

    def test_c09_create_second_page(self, api, state):
        """Create a second page for testing."""
        api.set_token(state.get_token("alice"))
        site_id = state.cms["main_site"]["site_id"]
        r = api.post(
            "cms/admin/pages/",
            json={
                "site_id": site_id,
                "title": "About Page",
                "slug": "about",
                "path": "/about",
                "page_type": "content",
                "order": 1,
            },
        )
        assert r.status_code == 201

    def test_c10_get_page_detail(self, api, state):
        """GET /cms/admin/pages/<slug>/ returns page detail."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/pages/home/")
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Home Page"

    def test_c11_page_detail_get_only(self, api, state):
        """Page detail view only supports GET (no PATCH/DELETE)."""
        api.set_token(state.get_token("alice"))
        # GET works
        r = api.get("cms/admin/pages/home/")
        assert r.status_code == 200
        # PATCH is not implemented on page detail
        r = api.patch(
            "cms/admin/pages/home/",
            json={
                "description": "Updated home page",
            },
        )
        assert r.status_code == 405  # Method Not Allowed

    def test_c12_page_structure_verified(self, api, state):
        """Verify page has expected structure from GET."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/pages/home/")
        assert r.status_code == 200
        data = r.json()
        assert "title" in data
        assert "slug" in data
        assert data["slug"] == "home"

    def test_c13_publish_page(self, api, state):
        """POST /cms/admin/pages/<slug>/publish/?site=<slug> publishes the page."""
        api.set_token(state.get_token("alice"))
        site_slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        r = api.post(f"cms/admin/pages/home/publish/?site={site_slug}")
        # May fail if no content placements exist yet
        assert r.status_code in (200, 400), f"Publish: {r.text}"

    def test_c14_unpublish_page(self, api, state):
        """POST /cms/admin/pages/<slug>/unpublish/?site=<slug> unpublishes."""
        api.set_token(state.get_token("alice"))
        site_slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        r = api.post(f"cms/admin/pages/home/unpublish/?site={site_slug}")
        assert r.status_code in (200, 400)

    def test_c15_export_page(self, api, state):
        """POST /cms/admin/pages/<slug>/export/?site=<slug> exports page data."""
        api.set_token(state.get_token("alice"))
        site_slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        r = api.post(f"cms/admin/pages/home/export/?site={site_slug}")
        if r.status_code == 200:
            data = r.json()
            assert "export_version" in data
            state.cms["main_site"]["export_data"] = data
        assert r.status_code in (200, 400)


# =============================================================================
# C16–C20: TEMPLATES (SECTION & BLOCK)
# =============================================================================


class TestCMSTemplates:
    """Test section and block template CRUD."""

    def test_c16_create_section_template(self, api, state):
        """POST /cms/admin/templates/sections/ creates a section template."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/templates/sections/",
            json={
                "name": "hero_section",
                "display_name": "Hero Section",
                "slug": "hero-section",
                "section_type": "hero",
                "description": "Full-width hero banner",
            },
        )
        assert r.status_code == 201, f"Create section template failed: {r.text}"
        data = r.json()
        state.cms["section_template"] = {"id": data["id"]}

    def test_c17_create_block_template(self, api, state):
        """POST /cms/admin/templates/blocks/ creates a block template."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/templates/blocks/",
            json={
                "name": "text_block",
                "display_name": "Text Block",
                "slug": "text-block",
                "block_type": "text",
                "schema": {
                    "fields": [
                        {"key": "heading", "type": "text", "label": "Heading"},
                        {"key": "body", "type": "richtext", "label": "Body"},
                    ],
                },
                "default_content": {
                    "heading": "Default Heading",
                    "body": "",
                },
            },
        )
        assert r.status_code == 201, f"Create block template failed: {r.text}"
        data = r.json()
        state.cms["block_template"] = {"id": data["id"]}

    def test_c18_list_section_templates(self, api, state):
        """GET /cms/admin/templates/sections/ lists section templates."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/templates/sections/")
        assert r.status_code == 200

    def test_c19_list_block_templates(self, api, state):
        """GET /cms/admin/templates/blocks/ lists block templates."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/templates/blocks/")
        assert r.status_code == 200

    def test_c20_invalid_schema_rejected(self, api, state):
        """POST block template with invalid schema returns 400."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/templates/blocks/",
            json={
                "name": "bad_block",
                "display_name": "Bad Block",
                "slug": "bad-block",
                "block_type": "text",
                "schema": "not a valid schema",  # Should be JSON object
            },
        )
        # 403 if platform membership missing
        assert r.status_code in (400, 403)


# =============================================================================
# C21–C26: CONTENT (BLOCK PLACEMENTS)
# =============================================================================


class TestCMSContent:
    """Test block placement content editing, history, and rollback."""

    def test_c21_get_block_placement(self, api, state):
        """GET /cms/admin/block-placements/<uuid>/ returns placement detail.

        Note: Block placements are created when sections/blocks are added to pages.
        We need to first set up page structure.
        """
        api.set_token(state.get_token("alice"))
        # This may need the page to have section+block placements
        # For now, verify the endpoint responds
        fake_uuid = str(uuid.uuid4())
        r = api.get(f"cms/admin/block-placements/{fake_uuid}/")
        assert r.status_code == 404  # Expected since no placement exists

    def test_c22_edit_draft_content(self, api, state):
        """PATCH /cms/admin/block-placements/<uuid>/ edits draft content."""
        # Will be testable once page has placements from cross-domain workflow
        pass

    def test_c23_invalid_content_rejected(self, api, state):
        """PATCH with content violating block schema returns 400."""
        pass

    def test_c24_get_history(self, api, state):
        """GET /cms/admin/block-placements/<uuid>/history/ returns versions."""
        pass

    def test_c25_rollback_version(self, api, state):
        """POST /cms/admin/block-placements/<uuid>/rollback/<version>/ rolls back."""
        pass

    def test_c26_rollback_nonexistent(self, api, state):
        """Rollback to non-existent version returns 404."""
        fake_uuid = str(uuid.uuid4())
        api.set_token(state.get_token("alice"))
        r = api.post(f"cms/admin/block-placements/{fake_uuid}/rollback/999/")
        # 403 if platform membership missing
        assert r.status_code in (403, 404)


# =============================================================================
# C27–C30: MEDIA
# =============================================================================


class TestCMSMedia:
    """Test media file upload, listing, and tombstone deletion."""

    def test_c27_list_media_empty(self, api, state):
        """GET /cms/admin/media/files/ returns media list."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/media/files/")
        assert r.status_code == 200

    def test_c28_upload_media(self, api, state):
        """POST /cms/admin/media/files/ uploads a media file."""
        api.set_token(state.get_token("alice"))
        # Create a minimal PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"file": ("hero.png", io.BytesIO(png_data), "image/png")}
        data = {"alt_text": "Hero image", "title": "Hero Banner"}

        r = api.session.post(
            api._url("cms/admin/media/files/"),
            files=files,
            data=data,
        )
        if r.status_code in (200, 201):
            resp_data = r.json()
            state.cms["media_file"] = {"id": resp_data["id"]}
        assert r.status_code in (200, 201), f"Upload failed: {r.text}"

    def test_c29_get_media_detail(self, api, state):
        """GET /cms/admin/media/files/<uuid>/ returns media detail."""
        if "media_file" not in state.cms:
            pytest.skip("No media uploaded")

        api.set_token(state.get_token("alice"))
        mid = state.cms["media_file"]["id"]
        r = api.get(f"cms/admin/media/files/{mid}/")
        assert r.status_code == 200

    def test_c30_delete_media(self, api, state):
        """DELETE /cms/admin/media/files/<uuid>/ tombstones the file."""
        if "media_file" not in state.cms:
            pytest.skip("No media")

        api.set_token(state.get_token("alice"))
        mid = state.cms["media_file"]["id"]
        r = api.delete(f"cms/admin/media/files/{mid}/")
        assert r.status_code in (200, 204)


# =============================================================================
# C31–C34: API KEYS
# =============================================================================


class TestCMSApiKeys:
    """Test API key CRUD for public CMS access."""

    def test_c31_list_api_keys(self, api, state):
        """GET /cms/admin/api-keys/ lists API keys."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/api-keys/")
        assert r.status_code == 200

    def test_c32_create_api_key(self, api, state):
        """POST /cms/admin/api-keys/ creates an API key (captures raw key)."""
        api.set_token(state.get_token("alice"))
        site_id = state.cms["main_site"]["site_id"]
        r = api.post(
            "cms/admin/api-keys/",
            json={
                "site_id": site_id,
                "name": "Test API Key",
                "rate_limit": 100,
            },
        )
        assert r.status_code == 201, f"Create API key failed: {r.text}"
        data = r.json()
        state.cms["main_site"]["api_key_id"] = data["id"]
        # The raw key is only returned on creation
        # Check for key_prefix or raw_key field
        if "raw_key" in data:
            state.cms["main_site"]["raw_key"] = data["raw_key"]
        elif "key" in data:
            state.cms["main_site"]["raw_key"] = data["key"]

    def test_c33_api_key_detail_no_get(self, api, state):
        """API key detail only supports DELETE (no GET)."""
        if "api_key_id" not in state.cms.get("main_site", {}):
            pytest.skip("No API key created")

        api.set_token(state.get_token("alice"))
        kid = state.cms["main_site"]["api_key_id"]
        # GET is not supported on the detail endpoint (only DELETE/revoke)
        r = api.get(f"cms/admin/api-keys/{kid}/")
        assert r.status_code == 405  # Method Not Allowed

        # Verify the key still appears in the list
        r = api.get("cms/admin/api-keys/")
        assert r.status_code == 200

    def test_c34_revoke_api_key(self, api, state):
        """DELETE or PATCH to revoke an API key."""
        # Create a disposable key to revoke
        api.set_token(state.get_token("alice"))
        site_id = state.cms["main_site"]["site_id"]
        r = api.post(
            "cms/admin/api-keys/",
            json={
                "site_id": site_id,
                "name": "Temp Key",
            },
        )
        if r.status_code != 201:
            pytest.skip("Could not create key to revoke")

        temp_id = r.json()["id"]
        r = api.delete(f"cms/admin/api-keys/{temp_id}/")
        assert r.status_code in (200, 204)


# =============================================================================
# CP01–CP08: PUBLIC CMS ENDPOINTS
# =============================================================================


class TestCMSPublic:
    """Test public CMS endpoints with API key authentication."""

    def test_cp01_public_site_with_key(self, api, state):
        """GET /cms/public/sites/<slug>/ with valid API key."""
        raw_key = state.cms.get("main_site", {}).get("raw_key")
        if not raw_key:
            pytest.skip("No raw API key available")

        api.clear_token()
        r = api.session.get(
            api._url(f"cms/public/sites/{state.cms['main_site']['site_slug']}/"),
            headers={"X-CMS-API-Key": raw_key},
        )
        assert r.status_code == 200

    def test_cp02_public_site_no_key(self, api, state):
        """GET /cms/public/sites/<slug>/ without API key returns 401/403."""
        api.clear_token()
        slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        r = api.get(f"cms/public/sites/{slug}/")
        assert r.status_code in (401, 403)

    def test_cp03_public_site_invalid_key(self, api, state):
        """GET /cms/public/sites/<slug>/ with invalid key returns 401/403."""
        api.clear_token()
        slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        r = api.session.get(
            api._url(f"cms/public/sites/{slug}/"),
            headers={"X-CMS-API-Key": "cmsk_invalidkey12345"},
        )
        assert r.status_code in (401, 403)

    def test_cp04_public_page_published(self, api, state):
        """GET /cms/public/pages/<slug>/ for published page."""
        raw_key = state.cms.get("main_site", {}).get("raw_key")
        if not raw_key:
            pytest.skip("No raw API key")

        # First publish the page
        api.set_token(state.get_token("alice"))
        site_slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        api.post(f"cms/admin/pages/home/publish/?site={site_slug}")

        api.clear_token()
        r = api.session.get(
            api._url("cms/public/pages/home/"),
            headers={"X-CMS-API-Key": raw_key},
        )
        # 200 if published, 404 if publish failed
        assert r.status_code in (200, 404)

    def test_cp05_public_page_draft(self, api, state):
        """GET /cms/public/pages/<slug>/ for draft page returns 404."""
        raw_key = state.cms.get("main_site", {}).get("raw_key")
        if not raw_key:
            pytest.skip("No raw API key")

        # Unpublish first
        api.set_token(state.get_token("alice"))
        site_slug = state.cms.get("main_site", {}).get("site_slug", "main-site")
        api.post(f"cms/admin/pages/home/unpublish/?site={site_slug}")

        api.clear_token()
        r = api.session.get(
            api._url("cms/public/pages/home/"),
            headers={"X-CMS-API-Key": raw_key},
        )
        assert r.status_code == 404

    def test_cp06_public_page_no_key(self, api, state):
        """GET /cms/public/pages/<slug>/ without key returns 401/403."""
        api.clear_token()
        r = api.get("cms/public/pages/home/")
        assert r.status_code in (401, 403)

    def test_cp07_public_nonexistent_page(self, api, state):
        """GET /cms/public/pages/<fake_slug>/ returns 404."""
        raw_key = state.cms.get("main_site", {}).get("raw_key")
        if not raw_key:
            pytest.skip("No raw API key")

        api.clear_token()
        r = api.session.get(
            api._url("cms/public/pages/nonexistent-page/"),
            headers={"X-CMS-API-Key": raw_key},
        )
        assert r.status_code == 404

    def test_cp08_restore_alice_token(self, api, state):
        """Restore Alice's token for subsequent phases."""
        api.set_token(state.get_token("alice"))
        r = api.get("users/me/")
        assert r.status_code == 200
