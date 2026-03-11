# apps/cms/managers.py
"""
CMS Managers & QuerySets
=========================
Custom managers for CMS models. Follows the same pattern as Form Builder:
- QuerySet for chainable helpers
- Manager extends SoftDeleteManager (for models with soft delete) or models.Manager
"""

from django.db import models
from apps.core.models import SoftDeleteManager
from apps.cms.constants import PageStatus, BlockPlacementStatus


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------

class SiteQuerySet(models.QuerySet):
    """Chainable query helpers for Site."""

    def active(self):
        return self.filter(is_active=True)

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)


class SiteManager(SoftDeleteManager):
    """Manager for Site with soft-delete support."""

    def get_queryset(self):
        return SiteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active(self):
        return self.get_queryset().active()

    def by_owner(self, **kwargs):
        return self.get_queryset().by_owner(**kwargs)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class PageQuerySet(models.QuerySet):
    """Chainable query helpers for Page."""

    def by_site(self, *, site_id):
        return self.filter(site_id=site_id)

    def published(self):
        return self.filter(status=PageStatus.PUBLISHED)

    def draft(self):
        return self.filter(status=PageStatus.DRAFT)

    def visible(self):
        return self.filter(is_visible=True)

    def with_section_placements(self):
        return self.prefetch_related(
            "section_placements__template",
            "section_placements__block_placements__template",
        )


class PageManager(SoftDeleteManager):
    """Manager for Page with soft-delete support."""

    def get_queryset(self):
        return PageQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def published(self):
        return self.get_queryset().published()

    def by_site(self, **kwargs):
        return self.get_queryset().by_site(**kwargs)


# ---------------------------------------------------------------------------
# SectionTemplate
# ---------------------------------------------------------------------------

class SectionTemplateQuerySet(models.QuerySet):
    """Chainable query helpers for SectionTemplate."""

    def by_type(self, *, section_type: str):
        return self.filter(section_type=section_type)


class SectionTemplateManager(SoftDeleteManager):
    """Manager for SectionTemplate with soft-delete support."""

    def get_queryset(self):
        return SectionTemplateQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def by_type(self, **kwargs):
        return self.get_queryset().by_type(**kwargs)


# ---------------------------------------------------------------------------
# BlockTemplate
# ---------------------------------------------------------------------------

class BlockTemplateQuerySet(models.QuerySet):
    """Chainable query helpers for BlockTemplate."""

    def by_type(self, *, block_type: str):
        return self.filter(block_type=block_type)


class BlockTemplateManager(SoftDeleteManager):
    """Manager for BlockTemplate with soft-delete support."""

    def get_queryset(self):
        return BlockTemplateQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def by_type(self, **kwargs):
        return self.get_queryset().by_type(**kwargs)


# ---------------------------------------------------------------------------
# MediaFolder
# ---------------------------------------------------------------------------

class MediaFolderQuerySet(models.QuerySet):
    """Chainable query helpers for MediaFolder."""

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)

    def root_folders(self):
        return self.filter(parent__isnull=True)


class MediaFolderManager(SoftDeleteManager):
    """Manager for MediaFolder with soft-delete support."""

    def get_queryset(self):
        return MediaFolderQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def by_owner(self, **kwargs):
        return self.get_queryset().by_owner(**kwargs)


# ---------------------------------------------------------------------------
# MediaFile
# ---------------------------------------------------------------------------

class MediaFileQuerySet(models.QuerySet):
    """Chainable query helpers for MediaFile."""

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)

    def by_folder(self, *, folder_id):
        return self.filter(folder_id=folder_id)

    def by_mime_type(self, *, mime_type: str):
        return self.filter(mime_type__startswith=mime_type)

    def tombstoned(self):
        return self.filter(is_tombstoned=True)

    def not_tombstoned(self):
        return self.filter(is_tombstoned=False)


class MediaFileManager(SoftDeleteManager):
    """Manager for MediaFile with soft-delete support."""

    def get_queryset(self):
        return MediaFileQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def tombstoned(self):
        return self.get_queryset().tombstoned()

    def by_owner(self, **kwargs):
        return self.get_queryset().by_owner(**kwargs)


# ---------------------------------------------------------------------------
# CMSApiKey
# ---------------------------------------------------------------------------

class CMSApiKeyQuerySet(models.QuerySet):
    """Chainable query helpers for CMSApiKey."""

    def by_site(self, *, site_id):
        return self.filter(site_id=site_id)

    def active(self):
        return self.filter(is_active=True)


class CMSApiKeyManager(SoftDeleteManager):
    """Manager for CMSApiKey with soft-delete support."""

    def get_queryset(self):
        return CMSApiKeyQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active(self):
        return self.get_queryset().active()

    def by_site(self, **kwargs):
        return self.get_queryset().by_site(**kwargs)
