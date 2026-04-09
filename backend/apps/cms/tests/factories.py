# apps/cms/tests/factories.py
import uuid

import factory

from apps.cms.constants import BlockPlacementStatus, ContentVersionAction, PageStatus
from apps.cms.models import (
    BlockTemplate,
    BlockTemplateActivation,
    CMSApiKey,
    ContentVersion,
    MediaFile,
    MediaFolder,
    Page,
    PageSectionPlacement,
    SectionBlockPlacement,
    SectionTemplate,
    SectionTemplateActivation,
    Site,
)
from apps.core.constants import OwnerType
from apps.users.tests.factories import UserFactory  # Canonical source


class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site

    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Test Site {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    domain = ""
    description = ""
    default_locale = "en"
    is_active = True
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class PageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Page

    site = factory.SubFactory(SiteFactory)
    title = factory.Sequence(lambda n: f"Test Page {n}")
    slug = factory.LazyAttribute(lambda obj: obj.title.lower().replace(" ", "-"))
    path = factory.LazyAttribute(lambda obj: f"/{obj.slug}")
    page_type = "content"
    status = PageStatus.DRAFT
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_visible = True
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class SectionTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SectionTemplate

    name = factory.Sequence(lambda n: f"section_template_{n}")
    display_name = factory.LazyAttribute(lambda obj: obj.name.replace("_", " ").title())
    slug = factory.LazyAttribute(lambda obj: obj.name)
    section_type = "content"
    description = ""
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class BlockTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockTemplate

    name = factory.Sequence(lambda n: f"block_template_{n}")
    display_name = factory.LazyAttribute(lambda obj: obj.name.replace("_", " ").title())
    slug = factory.LazyAttribute(lambda obj: obj.name)
    block_type = "text"
    schema = factory.LazyFunction(
        lambda: {
            "fields": [
                {
                    "key": "title",
                    "type": "text",
                    "label": "Title",
                    "required": True,
                    "validation": {"max_length": 200},
                },
                {
                    "key": "body",
                    "type": "textarea",
                    "label": "Body",
                    "required": False,
                },
            ]
        }
    )
    schema_version = 1
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class PageSectionPlacementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PageSectionPlacement

    page = factory.SubFactory(PageFactory)
    template = factory.SubFactory(SectionTemplateFactory)
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_visible = True


class SectionBlockPlacementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SectionBlockPlacement

    section_placement = factory.SubFactory(PageSectionPlacementFactory)
    template = factory.SubFactory(BlockTemplateFactory)
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_visible = True
    draft_content = factory.LazyFunction(lambda: {"title": "Default Title", "body": ""})
    status = BlockPlacementStatus.DRAFT
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class ContentVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContentVersion

    block_placement = factory.SubFactory(SectionBlockPlacementFactory)
    content_snapshot = factory.LazyFunction(lambda: {"title": "Snapshot"})
    version_number = factory.Sequence(lambda n: n + 1)
    action = ContentVersionAction.DRAFT_SAVE
    created_by = factory.SubFactory(UserFactory)


class MediaFolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MediaFolder

    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Folder {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    path = factory.LazyAttribute(lambda obj: f"/{obj.slug}/")
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class MediaFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MediaFile

    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(uuid.uuid4)
    storage_key = factory.Sequence(lambda n: f"platform/test/file_{n}.png")
    original_filename = factory.Sequence(lambda n: f"file_{n}.png")
    mime_type = "image/png"
    file_size = 1024
    is_tombstoned = False
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class SectionTemplateActivationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SectionTemplateActivation

    template = factory.SubFactory(SectionTemplateFactory)
    org_type = OwnerType.BUSINESS
    org_id = factory.LazyFunction(uuid.uuid4)
    is_active = True
    activated_by = factory.SubFactory(UserFactory)


class BlockTemplateActivationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockTemplateActivation

    template = factory.SubFactory(BlockTemplateFactory)
    org_type = OwnerType.BUSINESS
    org_id = factory.LazyFunction(uuid.uuid4)
    is_active = True
    activated_by = factory.SubFactory(UserFactory)


class CMSApiKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CMSApiKey

    site = factory.SubFactory(SiteFactory)
    name = factory.Sequence(lambda n: f"API Key {n}")
    key_prefix = "cmsk_test123"
    key_hash = factory.LazyFunction(lambda: CMSApiKey.generate_key()[2])
    allowed_origins = factory.LazyFunction(list)
    is_active = True
    rate_limit = 60
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)
