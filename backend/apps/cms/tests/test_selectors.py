# apps/cms/tests/test_selectors.py
import uuid
import pytest
from apps.core.exceptions import NotFound
from apps.cms.selectors import (
    CMSSiteSelector, CMSPageSelector, CMSTemplateSelector,
    CMSBlockPlacementSelector, CMSMediaSelector,
    CMSContentVersionSelector, CMSApiKeySelector,
)
from apps.cms.tests.factories import (
    SiteFactory, PageFactory, SectionTemplateFactory, BlockTemplateFactory,
    PageSectionPlacementFactory, SectionBlockPlacementFactory,
    ContentVersionFactory, MediaFileFactory, MediaFolderFactory,
    CMSApiKeyFactory,
)
from apps.cms.constants import PageStatus


@pytest.mark.django_db
class TestCMSSiteSelector:
    def test_get_by_slug(self, site):
        result = CMSSiteSelector.get_by_slug(
            owner_type=site.owner_type,
            owner_id=site.owner_id,
            slug=site.slug,
        )
        assert result.id == site.id

    def test_get_by_slug_not_found(self):
        with pytest.raises(NotFound):
            CMSSiteSelector.get_by_slug(
                owner_type="platform", owner_id=uuid.uuid4(), slug="nonexistent"
            )

    def test_get_by_id(self, site):
        result = CMSSiteSelector.get_by_id(site_id=site.id)
        assert result.id == site.id

    def test_get_by_id_not_found(self):
        with pytest.raises(NotFound):
            CMSSiteSelector.get_by_id(site_id=uuid.uuid4())

    def test_list_for_owner(self, site):
        result = CMSSiteSelector.list_for_owner(
            owner_type=site.owner_type, owner_id=site.owner_id,
        )
        assert site in result

    def test_list_for_owner_active_only(self, site, user):
        inactive_site = SiteFactory(
            owner_type=site.owner_type,
            owner_id=site.owner_id,
            is_active=False,
        )
        result = CMSSiteSelector.list_for_owner(
            owner_type=site.owner_type, owner_id=site.owner_id, active_only=True,
        )
        assert site in result
        assert inactive_site not in result


@pytest.mark.django_db
class TestCMSPageSelector:
    def test_get_by_slug(self, page):
        result = CMSPageSelector.get_by_slug(site_id=page.site_id, slug=page.slug)
        assert result.id == page.id

    def test_get_by_slug_not_found(self, site):
        with pytest.raises(NotFound):
            CMSPageSelector.get_by_slug(site_id=site.id, slug="nonexistent")

    def test_get_by_id(self, page):
        result = CMSPageSelector.get_by_id(page_id=page.id)
        assert result.id == page.id

    def test_get_with_full_tree(self, block_placement):
        page = block_placement.section_placement.page
        result = CMSPageSelector.get_with_full_tree(page_id=page.id)
        assert result.id == page.id
        # Verify prefetch worked
        placements = list(result.section_placements.all())
        assert len(placements) > 0

    def test_list_by_site(self, page):
        result = CMSPageSelector.list_by_site(site_id=page.site_id)
        assert page in result

    def test_list_by_site_with_status_filter(self, page):
        result = CMSPageSelector.list_by_site(
            site_id=page.site_id, status=PageStatus.DRAFT,
        )
        assert page in result

        result = CMSPageSelector.list_by_site(
            site_id=page.site_id, status=PageStatus.PUBLISHED,
        )
        assert page not in result

    def test_list_published_for_site(self, published_page):
        result = CMSPageSelector.list_published_for_site(site_id=published_page.site_id)
        assert published_page in result


@pytest.mark.django_db
class TestCMSTemplateSelector:
    def test_get_section_template_by_slug(self, section_template):
        result = CMSTemplateSelector.get_section_template_by_slug(slug=section_template.slug)
        assert result.id == section_template.id

    def test_get_section_template_not_found(self):
        with pytest.raises(NotFound):
            CMSTemplateSelector.get_section_template_by_slug(slug="nonexistent")

    def test_get_block_template_by_slug(self, block_template):
        result = CMSTemplateSelector.get_block_template_by_slug(slug=block_template.slug)
        assert result.id == block_template.id

    def test_get_block_template_by_id(self, block_template):
        result = CMSTemplateSelector.get_block_template_by_id(template_id=block_template.id)
        assert result.id == block_template.id

    def test_list_section_templates(self, section_template):
        result = CMSTemplateSelector.list_section_templates()
        assert section_template in result

    def test_list_section_templates_by_type(self, section_template):
        result = CMSTemplateSelector.list_section_templates(
            section_type=section_template.section_type,
        )
        assert section_template in result

    def test_list_block_templates(self, block_template):
        result = CMSTemplateSelector.list_block_templates()
        assert block_template in result


@pytest.mark.django_db
class TestCMSBlockPlacementSelector:
    def test_get_by_id(self, block_placement):
        result = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement.id
        )
        assert result.id == block_placement.id

    def test_get_by_id_not_found(self):
        with pytest.raises(NotFound):
            CMSBlockPlacementSelector.get_by_id(block_placement_id=uuid.uuid4())

    def test_list_for_section(self, block_placement):
        result = CMSBlockPlacementSelector.list_for_section(
            section_placement_id=block_placement.section_placement_id,
        )
        assert block_placement in result

    def test_list_for_page(self, block_placement):
        page = block_placement.section_placement.page
        result = CMSBlockPlacementSelector.list_for_page(page_id=page.id)
        assert block_placement in result


@pytest.mark.django_db
class TestCMSMediaSelector:
    def test_get_file_by_id(self, media_file):
        result = CMSMediaSelector.get_file_by_id(file_id=media_file.id)
        assert result.id == media_file.id

    def test_get_file_not_found(self):
        with pytest.raises(NotFound):
            CMSMediaSelector.get_file_by_id(file_id=uuid.uuid4())

    def test_list_files(self, media_file):
        result = CMSMediaSelector.list_files(
            owner_type=media_file.owner_type,
            owner_id=media_file.owner_id,
        )
        assert media_file in result

    def test_list_files_by_mime(self, media_file):
        result = CMSMediaSelector.list_files(
            owner_type=media_file.owner_type,
            owner_id=media_file.owner_id,
            mime_type="image",
        )
        assert media_file in result

    def test_get_folder_by_id(self, user):
        folder = MediaFolderFactory(created_by=user, updated_by=user)
        result = CMSMediaSelector.get_folder_by_id(folder_id=folder.id)
        assert result.id == folder.id

    def test_get_folder_by_id_not_found(self):
        with pytest.raises(NotFound):
            CMSMediaSelector.get_folder_by_id(folder_id=uuid.uuid4())


@pytest.mark.django_db
class TestCMSContentVersionSelector:
    def test_list_for_placement(self, block_placement, user):
        v1 = ContentVersionFactory(
            block_placement=block_placement, version_number=1, created_by=user,
        )
        v2 = ContentVersionFactory(
            block_placement=block_placement, version_number=2, created_by=user,
        )
        result = list(CMSContentVersionSelector.list_for_placement(
            block_placement_id=block_placement.id,
        ))
        assert result[0].version_number > result[1].version_number

    def test_get_version(self, block_placement, user):
        v = ContentVersionFactory(
            block_placement=block_placement, version_number=5, created_by=user,
        )
        result = CMSContentVersionSelector.get_version(
            block_placement_id=block_placement.id, version_number=5,
        )
        assert result.id == v.id

    def test_get_version_not_found(self, block_placement):
        with pytest.raises(NotFound):
            CMSContentVersionSelector.get_version(
                block_placement_id=block_placement.id, version_number=999,
            )

    def test_get_latest_version(self, block_placement, user):
        ContentVersionFactory(
            block_placement=block_placement, version_number=1, created_by=user,
        )
        ContentVersionFactory(
            block_placement=block_placement, version_number=3, created_by=user,
        )
        result = CMSContentVersionSelector.get_latest_version(
            block_placement_id=block_placement.id,
        )
        assert result.version_number == 3

    def test_get_latest_version_none(self, block_placement):
        result = CMSContentVersionSelector.get_latest_version(
            block_placement_id=block_placement.id,
        )
        assert result is None


@pytest.mark.django_db
class TestCMSApiKeySelector:
    def test_list_for_site(self):
        key = CMSApiKeyFactory()
        result = CMSApiKeySelector.list_for_site(site_id=key.site_id)
        assert key in result

    def test_get_by_hash(self):
        key = CMSApiKeyFactory()
        result = CMSApiKeySelector.get_by_hash(key_hash=key.key_hash)
        assert result.id == key.id

    def test_get_by_hash_not_found(self):
        with pytest.raises(NotFound):
            CMSApiKeySelector.get_by_hash(key_hash="nonexistent_hash")
