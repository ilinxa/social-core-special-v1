# apps/cms/api/views.py
"""
CMS API Views
==============
Admin and Public API views.

Admin views use PlatformContextMixin (platform-only).
Public views use CMS API key authentication.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.permissions import IsAuthenticated
from apps.core.pagination import StandardPagination
from apps.rbac.views import PlatformContextMixin
from apps.cms.models import Page
from apps.cms.constants import PageStatus
from apps.cms.services import (
    CMSSiteService, CMSTemplateService, CMSPageService,
    CMSContentService, CMSMediaService, CMSApiKeyService,
)
from apps.cms.selectors import (
    CMSSiteSelector, CMSPageSelector, CMSTemplateSelector,
    CMSBlockPlacementSelector, CMSMediaSelector,
    CMSContentVersionSelector, CMSApiKeySelector,
)
from apps.cms.api.serializers import (
    # Input serializers
    SiteCreateSerializer, SiteUpdateSerializer,
    PageCreateSerializer,
    SectionTemplateCreateSerializer, BlockTemplateCreateSerializer,
    DraftContentUpdateSerializer,
    MediaUploadSerializer, MediaUpdateSerializer,
    ApiKeyCreateSerializer,
    PageImportSerializer,
    # Output serializers
    SiteOutputSerializer, PageOutputSerializer, PageDetailOutputSerializer,
    SectionTemplateOutputSerializer, BlockTemplateOutputSerializer,
    BlockPlacementOutputSerializer,
    ContentVersionOutputSerializer,
    MediaFileOutputSerializer,
    ApiKeyOutputSerializer, ApiKeyCreatedOutputSerializer,
)


# ---------------------------------------------------------------------------
# Admin — Sites
# ---------------------------------------------------------------------------

class AdminSiteListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/sites/  -> List sites (platform-scoped)
    POST /api/v1/cms/admin/sites/  -> Create site (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SiteOutputSerializer(many=True))
    def get(self, request):
        actor_context = self.get_actor_context()
        sites = CMSSiteSelector.list_for_owner(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(sites, request)
        serializer = SiteOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=SiteCreateSerializer, responses=SiteOutputSerializer)
    def post(self, request):
        serializer = SiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site = CMSSiteService.create_site(
            actor_context=actor_context,
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            request=request,
            **serializer.validated_data,
        )
        return Response(SiteOutputSerializer(site).data, status=http_status.HTTP_201_CREATED)


class AdminSiteDetailView(PlatformContextMixin, APIView):
    """
    GET    /api/v1/cms/admin/sites/{slug}/  -> Get site details
    PATCH  /api/v1/cms/admin/sites/{slug}/  -> Update site
    DELETE /api/v1/cms/admin/sites/{slug}/  -> Delete site (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SiteOutputSerializer)
    def get(self, request, slug):
        actor_context = self.get_actor_context()
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=slug,
        )
        return Response(SiteOutputSerializer(site).data)

    @extend_schema(request=SiteUpdateSerializer, responses=SiteOutputSerializer)
    def patch(self, request, slug):
        serializer = SiteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site = CMSSiteService.update_site(
            actor_context=actor_context,
            slug=slug,
            request=request,
            **serializer.validated_data,
        )
        return Response(SiteOutputSerializer(site).data)

    @extend_schema(
        summary="Delete site",
        tags=["CMS - Admin"],
        responses={204: OpenApiResponse(description="Site deleted")},
    )
    def delete(self, request, slug):
        actor_context = self.get_actor_context()
        CMSSiteService.delete_site(
            actor_context=actor_context, slug=slug, request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin — Pages
# ---------------------------------------------------------------------------

class AdminPageListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/pages/  -> List pages (filterable by site, status)
    POST /api/v1/cms/admin/pages/  -> Create page (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PageOutputSerializer(many=True))
    def get(self, request):
        site_slug = request.query_params.get("site")
        status_filter = request.query_params.get("status")
        actor_context = self.get_actor_context()

        if site_slug:
            site = CMSSiteSelector.get_by_slug(
                owner_type=actor_context.account_type,
                owner_id=actor_context.account_id,
                slug=site_slug,
            )
            pages = CMSPageSelector.list_by_site(
                site_id=site.id, status=status_filter,
            )
        else:
            pages = Page.objects.filter(
                site__owner_type=actor_context.account_type,
                site__owner_id=actor_context.account_id,
            )
            if status_filter:
                pages = pages.filter(status=status_filter)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(pages, request)
        serializer = PageOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=PageCreateSerializer, responses=PageOutputSerializer)
    def post(self, request):
        serializer = PageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        page = CMSPageService.create_page(
            actor_context=actor_context,
            request=request,
            **serializer.validated_data,
        )
        return Response(PageOutputSerializer(page).data, status=http_status.HTTP_201_CREATED)


class AdminPageDetailView(PlatformContextMixin, APIView):
    """
    GET    /api/v1/cms/admin/pages/{slug}/  -> Get page (with optional depth)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PageDetailOutputSerializer)
    def get(self, request, slug):
        actor_context = self.get_actor_context()
        depth = request.query_params.get("depth", None)
        site_slug = request.query_params.get("site")

        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        ) if site_slug else None

        if depth == "full" and site:
            page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
            page = CMSPageSelector.get_with_full_tree(page_id=page.id)
            return Response(PageDetailOutputSerializer(page).data)

        if site:
            page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        else:
            page = Page.objects.filter(slug=slug).first()
            if not page:
                from apps.core.exceptions import NotFound
                raise NotFound(resource="Page", resource_id=slug)

        return Response(PageOutputSerializer(page).data)


class AdminPagePublishView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/publish/ -> Validate & publish page."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Publish page",
        tags=["CMS - Admin"],
        request=None,
        responses={200: PageOutputSerializer},
    )
    def post(self, request, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.publish_page(
            actor_context=actor_context, page_id=page.id, request=request,
        )
        return Response(PageOutputSerializer(page).data)


class AdminPageUnpublishView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/unpublish/ -> Revert to draft."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Unpublish page",
        tags=["CMS - Admin"],
        request=None,
        responses={200: PageOutputSerializer},
    )
    def post(self, request, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.unpublish_page(
            actor_context=actor_context, page_id=page.id, request=request,
        )
        return Response(PageOutputSerializer(page).data)


class AdminPageExportView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/export/ -> Export page tree as JSON."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Export page",
        tags=["CMS - Admin"],
        request=None,
    )
    def post(self, request, slug):
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        export_data = CMSPageService.export_page(
            actor_context=actor_context, page_id=page.id, request=request,
        )
        return Response(export_data)


class AdminPageImportView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/import/ -> Import page content."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Import page",
        tags=["CMS - Admin"],
        request=PageImportSerializer,
        responses={200: PageOutputSerializer},
    )
    def post(self, request, slug):
        serializer = PageImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.import_page(
            actor_context=actor_context,
            page_id=page.id,
            import_data=serializer.validated_data,
            request=request,
        )
        return Response(PageOutputSerializer(page).data)


# ---------------------------------------------------------------------------
# Admin — Templates
# ---------------------------------------------------------------------------

class AdminSectionTemplateListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/templates/sections/  -> List section templates
    POST /api/v1/cms/admin/templates/sections/  -> Create section template
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List section templates",
        tags=["CMS - Admin"],
        responses={200: SectionTemplateOutputSerializer(many=True)},
    )
    def get(self, request):
        section_type = request.query_params.get("section_type")
        templates = CMSTemplateSelector.list_section_templates(section_type=section_type)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = SectionTemplateOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create section template",
        tags=["CMS - Admin"],
        request=SectionTemplateCreateSerializer,
        responses={201: SectionTemplateOutputSerializer},
    )
    def post(self, request):
        serializer = SectionTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        template = CMSTemplateService.create_section_template(
            actor_context=actor_context, request=request,
            **serializer.validated_data,
        )
        return Response(
            SectionTemplateOutputSerializer(template).data,
            status=http_status.HTTP_201_CREATED,
        )


class AdminBlockTemplateListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/templates/blocks/  -> List block templates
    POST /api/v1/cms/admin/templates/blocks/  -> Create block template
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List block templates",
        tags=["CMS - Admin"],
        responses={200: BlockTemplateOutputSerializer(many=True)},
    )
    def get(self, request):
        block_type = request.query_params.get("block_type")
        templates = CMSTemplateSelector.list_block_templates(block_type=block_type)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = BlockTemplateOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create block template",
        tags=["CMS - Admin"],
        request=BlockTemplateCreateSerializer,
        responses={201: BlockTemplateOutputSerializer},
    )
    def post(self, request):
        serializer = BlockTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        template = CMSTemplateService.create_block_template(
            actor_context=actor_context, request=request,
            **serializer.validated_data,
        )
        return Response(
            BlockTemplateOutputSerializer(template).data,
            status=http_status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin — Block Placements (content interaction)
# ---------------------------------------------------------------------------

class AdminBlockPlacementDetailView(PlatformContextMixin, APIView):
    """
    GET   /api/v1/cms/admin/block-placements/{uuid}/ -> Get block placement
    PATCH /api/v1/cms/admin/block-placements/{uuid}/ -> Update draft_content
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get block placement",
        tags=["CMS - Admin"],
        responses={200: BlockPlacementOutputSerializer},
    )
    def get(self, request, uuid):
        placement = CMSBlockPlacementSelector.get_by_id(block_placement_id=uuid)
        return Response(BlockPlacementOutputSerializer(placement).data)

    @extend_schema(
        summary="Update draft content",
        tags=["CMS - Admin"],
        request=DraftContentUpdateSerializer,
        responses={200: BlockPlacementOutputSerializer},
    )
    def patch(self, request, uuid):
        serializer = DraftContentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        placement = CMSContentService.update_draft_content(
            actor_context=actor_context,
            block_placement_id=uuid,
            content=serializer.validated_data["draft_content"],
            request=request,
        )
        return Response(BlockPlacementOutputSerializer(placement).data)


class AdminBlockPlacementHistoryView(PlatformContextMixin, APIView):
    """GET /api/v1/cms/admin/block-placements/{uuid}/history/ -> List versions."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List content versions",
        tags=["CMS - Admin"],
        responses={200: ContentVersionOutputSerializer(many=True)},
    )
    def get(self, request, uuid):
        versions = CMSContentVersionSelector.list_for_placement(
            block_placement_id=uuid,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(versions, request)
        serializer = ContentVersionOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminBlockPlacementRollbackView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/block-placements/{uuid}/rollback/{version}/ -> Rollback."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Rollback content",
        tags=["CMS - Admin"],
        request=None,
        responses={200: BlockPlacementOutputSerializer},
    )
    def post(self, request, uuid, version_number):
        actor_context = self.get_actor_context()
        placement = CMSContentService.rollback_content(
            actor_context=actor_context,
            block_placement_id=uuid,
            version_number=version_number,
            request=request,
        )
        return Response(BlockPlacementOutputSerializer(placement).data)


# ---------------------------------------------------------------------------
# Admin — Media
# ---------------------------------------------------------------------------

class AdminMediaFileListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/media/files/  -> List files
    POST /api/v1/cms/admin/media/files/  -> Upload file
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List media files",
        tags=["CMS - Admin"],
        responses={200: MediaFileOutputSerializer(many=True)},
    )
    def get(self, request):
        actor_context = self.get_actor_context()
        folder_id = request.query_params.get("folder")
        mime_type = request.query_params.get("type")
        files = CMSMediaSelector.list_files(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            folder_id=folder_id,
            mime_type=mime_type,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(files, request)
        serializer = MediaFileOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Upload media file",
        tags=["CMS - Admin"],
        request=MediaUploadSerializer,
        responses={201: MediaFileOutputSerializer},
    )
    def post(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        media = CMSMediaService.upload_file(
            actor_context=actor_context,
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            request=request,
            **serializer.validated_data,
        )
        return Response(MediaFileOutputSerializer(media).data, status=http_status.HTTP_201_CREATED)


class AdminMediaFileDetailView(PlatformContextMixin, APIView):
    """
    GET    /api/v1/cms/admin/media/files/{uuid}/ -> Get file details
    PATCH  /api/v1/cms/admin/media/files/{uuid}/ -> Update file metadata
    DELETE /api/v1/cms/admin/media/files/{uuid}/ -> Delete file
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get media file",
        tags=["CMS - Admin"],
        responses={200: MediaFileOutputSerializer},
    )
    def get(self, request, uuid):
        media = CMSMediaSelector.get_file_by_id(file_id=uuid)
        return Response(MediaFileOutputSerializer(media).data)

    @extend_schema(
        summary="Update media file",
        tags=["CMS - Admin"],
        request=MediaUpdateSerializer,
        responses={200: MediaFileOutputSerializer},
    )
    def patch(self, request, uuid):
        serializer = MediaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        media = CMSMediaService.update_file(
            actor_context=actor_context,
            file_id=uuid,
            request=request,
            **serializer.validated_data,
        )
        return Response(MediaFileOutputSerializer(media).data)

    @extend_schema(
        summary="Delete media file",
        tags=["CMS - Admin"],
        responses={204: OpenApiResponse(description="File deleted")},
    )
    def delete(self, request, uuid):
        actor_context = self.get_actor_context()
        CMSMediaService.delete_file(
            actor_context=actor_context, file_id=uuid, request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin — API Keys
# ---------------------------------------------------------------------------

class AdminApiKeyListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/api-keys/ -> List API keys for a site
    POST /api/v1/cms/admin/api-keys/ -> Create API key (returns full key ONCE)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List API keys",
        tags=["CMS - Admin"],
        responses={200: ApiKeyOutputSerializer(many=True)},
    )
    def get(self, request):
        site_id = request.query_params.get("site")
        keys = CMSApiKeySelector.list_for_site(site_id=site_id)
        serializer = ApiKeyOutputSerializer(keys, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create API key",
        tags=["CMS - Admin"],
        request=ApiKeyCreateSerializer,
        responses={201: ApiKeyCreatedOutputSerializer},
    )
    def post(self, request):
        serializer = ApiKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        api_key, plaintext = CMSApiKeyService.create_api_key(
            actor_context=actor_context, request=request,
            **serializer.validated_data,
        )
        output = ApiKeyCreatedOutputSerializer(api_key).data
        output["key"] = plaintext  # Returned ONCE
        return Response(output, status=http_status.HTTP_201_CREATED)


class AdminApiKeyDetailView(PlatformContextMixin, APIView):
    """
    DELETE /api/v1/cms/admin/api-keys/{uuid}/ -> Revoke key
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Revoke API key",
        tags=["CMS - Admin"],
        responses={204: OpenApiResponse(description="API key revoked")},
    )
    def delete(self, request, uuid):
        actor_context = self.get_actor_context()
        CMSApiKeyService.revoke_api_key(
            actor_context=actor_context, api_key_id=uuid, request=request,
        )
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PublicSiteView(APIView):
    """GET /api/v1/cms/public/sites/{slug}/ -> Get published site info."""
    permission_classes = []  # API key checked in middleware

    @extend_schema(
        summary="Get public site",
        tags=["CMS - Public"],
        responses={200: SiteOutputSerializer},
    )
    def get(self, request, slug):
        site = getattr(request, "cms_site", None)
        if not site or site.slug != slug:
            from apps.core.exceptions import NotFound
            raise NotFound(resource="Site", resource_id=slug)
        return Response(SiteOutputSerializer(site).data)


class PublicPageView(APIView):
    """
    GET /api/v1/cms/public/pages/{slug}/ -> Get published page.
    Supports ?depth=full for full tree with published_content.
    """
    permission_classes = []

    @extend_schema(
        summary="Get public page",
        tags=["CMS - Public"],
        responses={200: PageDetailOutputSerializer},
    )
    def get(self, request, slug):
        site = getattr(request, "cms_site", None)
        if not site:
            from apps.core.exceptions import PermissionDenied
            raise PermissionDenied(message="Valid API key required")

        depth = request.query_params.get("depth")
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)

        if page.status != PageStatus.PUBLISHED or not page.is_visible:
            from apps.core.exceptions import NotFound
            raise NotFound(resource="Page", resource_id=slug)

        if depth == "full":
            page = CMSPageSelector.get_with_full_tree(page_id=page.id)
            return Response(PageDetailOutputSerializer(page, context={"public": True}).data)

        return Response(PageOutputSerializer(page).data)
