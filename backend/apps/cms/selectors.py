# apps/cms/selectors.py
"""
CMS Selectors
==============
Read-only queries for CMS models. All methods use keyword-only arguments.
"""

from typing import Optional
from uuid import UUID
from django.db.models import QuerySet, Prefetch

from apps.core.exceptions import NotFound
from apps.cms.models import (
    Site, Page, SectionTemplate, BlockTemplate,
    PageSectionPlacement, SectionBlockPlacement,
    ContentVersion, MediaFolder, MediaFile, MediaUsage, CMSApiKey,
)
from apps.cms.constants import PageStatus, ContentLayer


class CMSSiteSelector:
    """Read-only queries for Site."""

    @staticmethod
    def get_by_slug(*, owner_type: str, owner_id: UUID, slug: str) -> Site:
        site = Site.objects.filter(
            owner_type=owner_type, owner_id=owner_id, slug=slug
        ).first()
        if not site:
            raise NotFound(resource="Site", resource_id=slug)
        return site

    @staticmethod
    def get_by_id(*, site_id: UUID) -> Site:
        site = Site.objects.filter(id=site_id).first()
        if not site:
            raise NotFound(resource="Site", resource_id=site_id)
        return site

    @staticmethod
    def list_for_owner(
        *, owner_type: str, owner_id: UUID, active_only: bool = False
    ) -> QuerySet[Site]:
        qs = Site.objects.filter(owner_type=owner_type, owner_id=owner_id)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs


class CMSPageSelector:
    """Read-only queries for Page with depth control."""

    @staticmethod
    def get_by_slug(*, site_id: UUID, slug: str) -> Page:
        page = Page.objects.filter(site_id=site_id, slug=slug).first()
        if not page:
            raise NotFound(resource="Page", resource_id=slug)
        return page

    @staticmethod
    def get_by_id(*, page_id: UUID) -> Page:
        page = Page.objects.filter(id=page_id).first()
        if not page:
            raise NotFound(resource="Page", resource_id=page_id)
        return page

    @staticmethod
    def get_with_full_tree(*, page_id: UUID) -> Page:
        """
        Get page with full tree: sections -> blocks -> templates.
        Uses prefetch_related for efficient loading (3 joins deep).
        """
        page = (
            Page.objects
            .filter(id=page_id)
            .prefetch_related(
                Prefetch(
                    "section_placements",
                    queryset=PageSectionPlacement.objects.select_related("template").order_by("order"),
                ),
                Prefetch(
                    "section_placements__block_placements",
                    queryset=SectionBlockPlacement.objects.select_related("template").order_by("order"),
                ),
            )
            .first()
        )
        if not page:
            raise NotFound(resource="Page", resource_id=page_id)
        return page

    @staticmethod
    def list_by_site(
        *,
        site_id: UUID,
        status: Optional[str] = None,
        visible_only: bool = False,
    ) -> QuerySet[Page]:
        qs = Page.objects.filter(site_id=site_id)
        if status:
            qs = qs.filter(status=status)
        if visible_only:
            qs = qs.filter(is_visible=True)
        return qs.order_by("order")

    @staticmethod
    def list_published_for_site(*, site_id: UUID) -> QuerySet[Page]:
        """List published, visible pages for public API."""
        return (
            Page.objects
            .filter(site_id=site_id, status=PageStatus.PUBLISHED, is_visible=True)
            .order_by("order")
        )


class CMSTemplateSelector:
    """Read-only queries for SectionTemplate and BlockTemplate."""

    @staticmethod
    def get_section_template_by_slug(*, slug: str) -> SectionTemplate:
        template = SectionTemplate.objects.filter(slug=slug).first()
        if not template:
            raise NotFound(resource="SectionTemplate", resource_id=slug)
        return template

    @staticmethod
    def get_block_template_by_slug(*, slug: str) -> BlockTemplate:
        template = BlockTemplate.objects.filter(slug=slug).first()
        if not template:
            raise NotFound(resource="BlockTemplate", resource_id=slug)
        return template

    @staticmethod
    def get_block_template_by_id(*, template_id: UUID) -> BlockTemplate:
        template = BlockTemplate.objects.filter(id=template_id).first()
        if not template:
            raise NotFound(resource="BlockTemplate", resource_id=template_id)
        return template

    @staticmethod
    def list_section_templates(
        *, section_type: Optional[str] = None
    ) -> QuerySet[SectionTemplate]:
        qs = SectionTemplate.objects.all()
        if section_type:
            qs = qs.filter(section_type=section_type)
        return qs

    @staticmethod
    def list_block_templates(
        *, block_type: Optional[str] = None
    ) -> QuerySet[BlockTemplate]:
        qs = BlockTemplate.objects.all()
        if block_type:
            qs = qs.filter(block_type=block_type)
        return qs


class CMSBlockPlacementSelector:
    """Read-only queries for SectionBlockPlacement."""

    @staticmethod
    def get_by_id(*, block_placement_id: UUID) -> SectionBlockPlacement:
        placement = (
            SectionBlockPlacement.objects
            .select_related("template", "section_placement__page")
            .filter(id=block_placement_id)
            .first()
        )
        if not placement:
            raise NotFound(resource="SectionBlockPlacement", resource_id=block_placement_id)
        return placement

    @staticmethod
    def list_for_section(*, section_placement_id: UUID) -> QuerySet[SectionBlockPlacement]:
        return (
            SectionBlockPlacement.objects
            .filter(section_placement_id=section_placement_id)
            .select_related("template")
            .order_by("order")
        )

    @staticmethod
    def list_for_page(*, page_id: UUID) -> QuerySet[SectionBlockPlacement]:
        """Get all block placements for a page (across all sections)."""
        return (
            SectionBlockPlacement.objects
            .filter(section_placement__page_id=page_id)
            .select_related("template", "section_placement")
            .order_by("section_placement__order", "order")
        )


class CMSMediaSelector:
    """Read-only queries for MediaFolder and MediaFile."""

    @staticmethod
    def get_file_by_id(*, file_id: UUID) -> MediaFile:
        media = MediaFile.objects.filter(id=file_id).first()
        if not media:
            raise NotFound(resource="MediaFile", resource_id=file_id)
        return media

    @staticmethod
    def list_files(
        *,
        owner_type: str,
        owner_id: UUID,
        folder_id: Optional[UUID] = None,
        mime_type: Optional[str] = None,
    ) -> QuerySet[MediaFile]:
        qs = MediaFile.objects.filter(owner_type=owner_type, owner_id=owner_id)
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        if mime_type:
            qs = qs.filter(mime_type__startswith=mime_type)
        return qs

    @staticmethod
    def get_usage(*, file_id: UUID) -> QuerySet[MediaUsage]:
        return MediaUsage.objects.filter(media_file_id=file_id).select_related(
            "block_placement__section_placement__page"
        )

    @staticmethod
    def list_folders(
        *, owner_type: str, owner_id: UUID, parent_id: Optional[UUID] = None
    ) -> QuerySet[MediaFolder]:
        qs = MediaFolder.objects.filter(owner_type=owner_type, owner_id=owner_id)
        if parent_id:
            qs = qs.filter(parent_id=parent_id)
        else:
            qs = qs.filter(parent__isnull=True)
        return qs

    @staticmethod
    def get_folder_by_slug(
        *, owner_type: str, owner_id: UUID, slug: str
    ) -> MediaFolder:
        folder = MediaFolder.objects.filter(
            owner_type=owner_type, owner_id=owner_id, slug=slug
        ).first()
        if not folder:
            raise NotFound(resource="MediaFolder", resource_id=slug)
        return folder

    @staticmethod
    def get_folder_by_id(*, folder_id: UUID) -> MediaFolder:
        folder = MediaFolder.objects.filter(id=folder_id).first()
        if not folder:
            raise NotFound(resource="MediaFolder", resource_id=folder_id)
        return folder


class CMSContentVersionSelector:
    """Read-only queries for ContentVersion."""

    @staticmethod
    def list_for_placement(*, block_placement_id: UUID) -> QuerySet[ContentVersion]:
        return (
            ContentVersion.objects
            .filter(block_placement_id=block_placement_id)
            .select_related("created_by")
            .order_by("-version_number")
        )

    @staticmethod
    def get_version(
        *, block_placement_id: UUID, version_number: int
    ) -> ContentVersion:
        version = ContentVersion.objects.filter(
            block_placement_id=block_placement_id,
            version_number=version_number,
        ).first()
        if not version:
            raise NotFound(
                resource="ContentVersion",
                resource_id=f"{block_placement_id}:v{version_number}",
            )
        return version

    @staticmethod
    def get_latest_version(*, block_placement_id: UUID) -> Optional[ContentVersion]:
        return (
            ContentVersion.objects
            .filter(block_placement_id=block_placement_id)
            .order_by("-version_number")
            .first()
        )


class CMSApiKeySelector:
    """Read-only queries for CMSApiKey."""

    @staticmethod
    def get_by_hash(*, key_hash: str) -> CMSApiKey:
        api_key = CMSApiKey.objects.filter(key_hash=key_hash, is_deleted=False).first()
        if not api_key:
            raise NotFound(resource="CMSApiKey", resource_id="(hashed)")
        return api_key

    @staticmethod
    def list_for_site(*, site_id: UUID) -> QuerySet[CMSApiKey]:
        return CMSApiKey.objects.filter(site_id=site_id, is_deleted=False)
