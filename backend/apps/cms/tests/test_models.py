# apps/cms/tests/test_models.py
import pytest
from django.db import IntegrityError
from apps.cms.tests.factories import (
    SiteFactory, PageFactory, SectionTemplateFactory, BlockTemplateFactory,
    PageSectionPlacementFactory, SectionBlockPlacementFactory,
    ContentVersionFactory, MediaFolderFactory, MediaFileFactory, CMSApiKeyFactory,
)
from apps.cms.models import CMSApiKey


@pytest.mark.django_db
class TestSiteModel:
    def test_site_str(self, site):
        assert str(site) == site.name

    def test_unique_slug_per_owner(self, site):
        """Duplicate slug within same owner raises IntegrityError."""
        with pytest.raises(IntegrityError):
            SiteFactory(
                owner_type=site.owner_type,
                owner_id=site.owner_id,
                slug=site.slug,
            )

    def test_different_owners_same_slug(self, site):
        """Different owners can have the same slug."""
        import uuid
        other_site = SiteFactory(
            owner_type=site.owner_type,
            owner_id=uuid.uuid4(),
            slug=site.slug,
        )
        assert other_site.slug == site.slug

    def test_soft_delete_allows_slug_reuse(self, site, user):
        """Soft-deleted site slug can be reused."""
        slug = site.slug
        site.soft_delete(user=user)
        new_site = SiteFactory(
            owner_type=site.owner_type,
            owner_id=site.owner_id,
            slug=slug,
        )
        assert new_site.slug == slug


@pytest.mark.django_db
class TestPageModel:
    def test_page_str(self, page):
        assert str(page) == f"{page.title} ({page.site.name})"

    def test_unique_order_per_site(self, page):
        """Duplicate order within same site raises IntegrityError."""
        with pytest.raises(IntegrityError):
            PageFactory(site=page.site, order=page.order)

    def test_unique_path_per_site(self, page):
        """Duplicate path within same site raises IntegrityError."""
        with pytest.raises(IntegrityError):
            PageFactory(site=page.site, path=page.path, order=999)

    def test_unique_slug_per_site(self, page):
        """Duplicate slug within same site raises IntegrityError."""
        with pytest.raises(IntegrityError):
            PageFactory(site=page.site, slug=page.slug, path="/other", order=999)


@pytest.mark.django_db
class TestSectionTemplateModel:
    def test_template_str(self, section_template):
        assert str(section_template) == section_template.display_name

    def test_unique_slug_active(self):
        """Duplicate slug on active templates raises IntegrityError."""
        t1 = SectionTemplateFactory(slug="unique-section-slug")
        with pytest.raises(IntegrityError):
            SectionTemplateFactory(slug="unique-section-slug")

    def test_soft_delete_allows_slug_reuse(self, user):
        """Soft-deleted template slug can be reused."""
        t = SectionTemplateFactory(slug="reusable-section-slug")
        t.soft_delete(user=user)
        t2 = SectionTemplateFactory(slug="reusable-section-slug")
        assert t2.slug == "reusable-section-slug"


@pytest.mark.django_db
class TestBlockTemplateModel:
    def test_template_str(self, block_template):
        assert str(block_template) == f"{block_template.display_name} (v{block_template.schema_version})"

    def test_schema_version_default(self, block_template):
        assert block_template.schema_version == 1


@pytest.mark.django_db
class TestPageSectionPlacementModel:
    def test_unique_order_per_page(self, section_placement):
        """Duplicate order within same page raises IntegrityError."""
        with pytest.raises(IntegrityError):
            PageSectionPlacementFactory(
                page=section_placement.page,
                order=section_placement.order,
            )


@pytest.mark.django_db
class TestSectionBlockPlacementModel:
    def test_unique_order_per_section(self, block_placement):
        """Duplicate order within same section raises IntegrityError."""
        with pytest.raises(IntegrityError):
            SectionBlockPlacementFactory(
                section_placement=block_placement.section_placement,
                order=block_placement.order,
            )

    def test_draft_content_default(self):
        bp = SectionBlockPlacementFactory()
        assert bp.draft_content is not None
        assert isinstance(bp.draft_content, dict)


@pytest.mark.django_db
class TestContentVersionModel:
    def test_version_str(self):
        version = ContentVersionFactory(version_number=3)
        assert "v3" in str(version)


@pytest.mark.django_db
class TestMediaFolderModel:
    def test_folder_str(self):
        folder = MediaFolderFactory(name="Images", path="")
        assert str(folder) == "Images"


@pytest.mark.django_db
class TestMediaFileModel:
    def test_file_str(self):
        media = MediaFileFactory(original_filename="photo.jpg")
        assert str(media) == "photo.jpg"

    def test_tombstoned_default_false(self):
        media = MediaFileFactory()
        assert media.is_tombstoned is False


@pytest.mark.django_db
class TestCMSApiKeyModel:
    def test_generate_key(self):
        plaintext, prefix, key_hash = CMSApiKey.generate_key()
        assert plaintext.startswith("cmsk_")
        assert prefix == plaintext[:12]
        assert len(key_hash) == 64  # SHA-256 hex

    def test_hash_key_consistency(self):
        plaintext, prefix, key_hash = CMSApiKey.generate_key()
        assert CMSApiKey.hash_key(plaintext) == key_hash

    def test_api_key_str(self):
        key = CMSApiKeyFactory()
        assert key.key_prefix in str(key)
