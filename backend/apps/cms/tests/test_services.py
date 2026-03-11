# apps/cms/tests/test_services.py
import pytest
from apps.core.exceptions import (
    ValidationError, ConflictError, BusinessRuleViolation, NotFound,
)
from apps.cms.services import (
    CMSSiteService, CMSTemplateService, CMSPageService,
    CMSContentService, CMSApiKeyService,
)
from apps.cms.constants import PageStatus, BlockPlacementStatus
from apps.cms.tests.factories import (
    SiteFactory, PageFactory, ContentVersionFactory,
    SectionBlockPlacementFactory, PageSectionPlacementFactory,
)
from apps.core.constants import OwnerType


@pytest.mark.django_db
class TestCMSSiteService:
    def test_create_site(self, actor_context, platform_with_rbac):
        site = CMSSiteService.create_site(
            actor_context=actor_context,
            name="My Site",
            slug="my-site",
            owner_type=OwnerType.PLATFORM,
            owner_id=platform_with_rbac.id,
        )
        assert site.name == "My Site"
        assert site.slug == "my-site"

    def test_create_site_duplicate_slug(self, actor_context, site):
        with pytest.raises(ConflictError):
            CMSSiteService.create_site(
                actor_context=actor_context,
                name="Another",
                slug=site.slug,
                owner_type=site.owner_type,
                owner_id=site.owner_id,
            )

    def test_update_site(self, actor_context, site):
        updated = CMSSiteService.update_site(
            actor_context=actor_context,
            slug=site.slug,
            name="Updated Name",
        )
        assert updated.name == "Updated Name"

    def test_delete_site(self, actor_context, site):
        CMSSiteService.delete_site(
            actor_context=actor_context,
            slug=site.slug,
        )
        site.refresh_from_db()
        assert site.is_deleted is True


@pytest.mark.django_db
class TestCMSTemplateService:
    def test_create_section_template(self, actor_context):
        template = CMSTemplateService.create_section_template(
            actor_context=actor_context,
            name="hero_section",
            display_name="Hero Section",
            slug="hero-section",
            section_type="hero",
        )
        assert template.slug == "hero-section"

    def test_create_section_template_duplicate_slug(self, actor_context, section_template):
        with pytest.raises(ConflictError):
            CMSTemplateService.create_section_template(
                actor_context=actor_context,
                name="dup",
                display_name="Dup",
                slug=section_template.slug,
                section_type="content",
            )

    def test_create_block_template(self, actor_context):
        schema = {
            "fields": [
                {"key": "heading", "type": "text", "required": True},
            ]
        }
        template = CMSTemplateService.create_block_template(
            actor_context=actor_context,
            name="heading_block",
            display_name="Heading Block",
            slug="heading-block",
            block_type="heading",
            schema=schema,
        )
        assert template.schema_version == 1
        assert template.schema == schema

    def test_create_block_template_invalid_schema(self, actor_context):
        with pytest.raises(ValidationError):
            CMSTemplateService.create_block_template(
                actor_context=actor_context,
                name="bad",
                display_name="Bad",
                slug="bad-block",
                block_type="bad",
                schema={},  # Missing "fields"
            )

    def test_update_block_schema(self, actor_context, block_template):
        new_schema = {
            "fields": [
                {"key": "title", "type": "text", "required": True},
                {"key": "subtitle", "type": "text", "required": False},
            ]
        }
        result = CMSTemplateService.update_block_schema(
            actor_context=actor_context,
            template_id=block_template.id,
            schema=new_schema,
        )
        assert result.schema_version == 2
        assert len(result.schema["fields"]) == 2

    def test_reorder_section_placements(self, actor_context, page, section_template, user):
        from apps.cms.tests.factories import SectionTemplateFactory
        t2 = SectionTemplateFactory(created_by=user, updated_by=user)
        sp1 = PageSectionPlacementFactory(page=page, template=section_template, order=0)
        sp2 = PageSectionPlacementFactory(page=page, template=t2, order=1)

        CMSTemplateService.reorder_section_placements(
            actor_context=actor_context,
            page_id=page.id,
            ordered_placement_ids=[sp2.id, sp1.id],
        )

        sp1.refresh_from_db()
        sp2.refresh_from_db()
        assert sp2.order == 0
        assert sp1.order == 1

    def test_reorder_section_placements_wrong_ids(self, actor_context, page):
        import uuid
        with pytest.raises(ValidationError):
            CMSTemplateService.reorder_section_placements(
                actor_context=actor_context,
                page_id=page.id,
                ordered_placement_ids=[uuid.uuid4()],
            )


@pytest.mark.django_db
class TestCMSPageService:
    def test_create_page(self, actor_context, site):
        page = CMSPageService.create_page(
            actor_context=actor_context,
            site_id=site.id,
            title="New Page",
            slug="new-page",
            path="/new-page",
            page_type="content",
            order=0,
        )
        assert page.status == PageStatus.DRAFT
        assert page.site_id == site.id

    def test_create_page_duplicate_slug(self, actor_context, page):
        with pytest.raises(ConflictError):
            CMSPageService.create_page(
                actor_context=actor_context,
                site_id=page.site_id,
                title="Another",
                slug=page.slug,
                path="/another",
                page_type="content",
                order=999,
            )

    def test_publish_page_copies_draft_to_published(self, actor_context, page, block_placement):
        block_placement.draft_content = {"title": "Hello World", "body": "Content"}
        block_placement.save()

        result = CMSPageService.publish_page(
            actor_context=actor_context, page_id=page.id,
        )

        block_placement.refresh_from_db()
        assert block_placement.published_content == {"title": "Hello World", "body": "Content"}
        assert block_placement.status == BlockPlacementStatus.PUBLISHED
        assert result.status == PageStatus.PUBLISHED
        assert result.published_at is not None

    def test_publish_page_validates_all_blocks(self, actor_context, page, block_placement):
        """Publish fails if required fields are empty."""
        block_placement.draft_content = {"title": "", "body": ""}
        block_placement.is_visible = True
        block_placement.save()

        with pytest.raises(ValidationError) as exc:
            CMSPageService.publish_page(
                actor_context=actor_context, page_id=page.id,
            )
        assert "publish_errors" in exc.value.details

    def test_unpublish_reverts_status(self, actor_context, published_page):
        page = CMSPageService.unpublish_page(
            actor_context=actor_context, page_id=published_page.id,
        )
        assert page.status == PageStatus.DRAFT

    def test_unpublish_draft_page_fails(self, actor_context, page):
        with pytest.raises(BusinessRuleViolation):
            CMSPageService.unpublish_page(
                actor_context=actor_context, page_id=page.id,
            )

    def test_export_page(self, actor_context, page, block_placement):
        export_data = CMSPageService.export_page(
            actor_context=actor_context, page_id=page.id,
        )
        assert export_data["export_version"] == "3.1"
        assert "page" in export_data
        assert export_data["page"]["slug"] == page.slug

    def test_reorder_pages(self, actor_context, site, user):
        p1 = PageFactory(site=site, order=0, slug="p1", path="/p1", created_by=user, updated_by=user)
        p2 = PageFactory(site=site, order=1, slug="p2", path="/p2", created_by=user, updated_by=user)

        CMSPageService.reorder_pages(
            actor_context=actor_context,
            site_id=site.id,
            ordered_page_ids=[p2.id, p1.id],
        )
        p1.refresh_from_db()
        p2.refresh_from_db()
        assert p2.order == 0
        assert p1.order == 1


@pytest.mark.django_db
class TestCMSContentService:
    def test_update_draft_content(self, actor_context, block_placement):
        result = CMSContentService.update_draft_content(
            actor_context=actor_context,
            block_placement_id=block_placement.id,
            content={"title": "Updated", "body": "New content"},
        )
        assert result.draft_content == {"title": "Updated", "body": "New content"}

    def test_rollback_restores_from_version(self, actor_context, block_placement, user):
        ContentVersionFactory(
            block_placement=block_placement,
            content_snapshot={"title": "Version 1"},
            version_number=1,
            created_by=user,
        )

        result = CMSContentService.rollback_content(
            actor_context=actor_context,
            block_placement_id=block_placement.id,
            version_number=1,
        )
        assert result.draft_content == {"title": "Version 1"}

    def test_toggle_visibility(self, actor_context, block_placement):
        result = CMSContentService.toggle_visibility(
            actor_context=actor_context,
            block_placement_id=block_placement.id,
            is_visible=False,
        )
        assert result.is_visible is False

    def test_toggle_visibility_fails_for_required(self, actor_context, block_placement):
        block_placement.is_required = True
        block_placement.save()

        with pytest.raises(BusinessRuleViolation):
            CMSContentService.toggle_visibility(
                actor_context=actor_context,
                block_placement_id=block_placement.id,
                is_visible=False,
            )


@pytest.mark.django_db
class TestCMSApiKeyService:
    def test_create_api_key(self, actor_context, site):
        api_key, plaintext = CMSApiKeyService.create_api_key(
            actor_context=actor_context,
            site_id=site.id,
            name="Test Key",
        )
        assert plaintext.startswith("cmsk_")
        assert api_key.is_active is True

    def test_revoke_api_key(self, actor_context, site):
        api_key, _ = CMSApiKeyService.create_api_key(
            actor_context=actor_context,
            site_id=site.id,
            name="To Revoke",
        )
        revoked = CMSApiKeyService.revoke_api_key(
            actor_context=actor_context,
            api_key_id=api_key.id,
        )
        assert revoked.is_active is False
        assert revoked.is_deleted is True

    def test_validate_api_key(self, actor_context, site):
        api_key, plaintext = CMSApiKeyService.create_api_key(
            actor_context=actor_context,
            site_id=site.id,
            name="Validate Me",
        )
        validated = CMSApiKeyService.validate_api_key(plaintext_key=plaintext)
        assert validated.id == api_key.id
